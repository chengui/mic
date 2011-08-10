#!/usr/bin/python
import os.path
import sys
import subprocess
import logging
import shutil

from micng.pluginbase.imager_plugin import ImagerPlugin
import micng.chroot as chroot
import micng.utils.misc as misc
import micng.utils.fs_related as fs_related
import micng.utils.cmdln as cmdln
import micng.configmgr as configmgr
import micng.pluginmgr as pluginmgr
import micng.imager.livecd as livecd
from micng.utils.errors import *

class LiveCDPlugin(ImagerPlugin):

    @classmethod
    def do_create(self, subcmd, opts, *args):
        """${cmd_name}: create livecd image

        ${cmd_usage}
        ${cmd_option_list}
        """
        if len(args) == 0:
            return
        if len(args) == 1:
            ksconf = args[0]
        else:
            raise errors.Usage("Extra arguments given")

        cfgmgr = configmgr.getConfigMgr()
        cfgmgr.setProperty("ksconf", ksconf)
        creatoropts = cfgmgr.create
        plgmgr = pluginmgr.PluginMgr()
        plgmgr.loadPlugins()
        
        for (key, pcls) in plgmgr.getBackendPlugins():
            if key == creatoropts['pkgmgr']:
                pkgmgr = pcls

        if not pkgmgr:
            raise CreatorError("Can't find backend %s" % pkgmgr)

        creator = livecd.LiveCDImageCreator(creatoropts, pkgmgr)
        try:
            creator.check_depend_tools()
            creator.mount(None, creatoropts["cachedir"])
            creator.install()
            creator.configure(creatoropts["repomd"])
            creator.unmount()
            creator.package(creatoropts["outdir"])
            outimage = creator.outimage
            creator.print_outimage_info()
            outimage = creator.outimage
        except CreatorError, e:
            raise CreatorError("failed to create image : %s" % e)
        finally:
            creator.cleanup()
#        if not creatoropts["image_info"]:
            print "Finished."
        return 0

    @classmethod
    def do_chroot(cls, target):
        img = target
        imgmnt = misc.mkdtemp()
        imgloop = fs_related.DiskMount(fs_related.LoopbackDisk(img, 0), imgmnt)
        try:
            imgloop.mount()
        except MountError, e:
            imgloop.cleanup()
            raise CreatorError("Failed to loopback mount '%s' : %s" %(img, e))

        # legacy LiveOS filesystem layout support, remove for F9 or F10
        if os.path.exists(imgmnt + "/squashfs.img"):
            squashimg = imgmnt + "/squashfs.img"
        else:
            squashimg = imgmnt + "/LiveOS/squashfs.img"

        tmpoutdir = misc.mkdtemp()
        # unsquashfs requires outdir mustn't exist
        shutil.rmtree(tmpoutdir, ignore_errors = True)
        misc.uncompress_squashfs(squashimg, tmpoutdir)

        # legacy LiveOS filesystem layout support, remove for F9 or F10
        if os.path.exists(tmpoutdir + "/os.img"):
            os_image = tmpoutdir + "/os.img"
        else:
            os_image = tmpoutdir + "/LiveOS/ext3fs.img"

        if not os.path.exists(os_image):
            imgloop.cleanup()
            shutil.rmtree(tmpoutdir, ignore_errors = True)
            shutil.rmtree(imgmnt, ignore_errors = True)
            raise CreatorError("'%s' is not a valid live CD ISO : neither "
                               "LiveOS/ext3fs.img nor os.img exist" %img)

        #unpack image to target dir
        imgsize = misc.get_file_size(os_image) * 1024L * 1024L
        extmnt = misc.mkdtemp()
        tfstype = "ext3"
        tlabel = "ext3 label"
        MyDiskMount = fs_related.ExtDiskMount
        #if misc.fstype_is_btrfs(os_image):
        #    tfstype = "btrfs"
        #    tlabel = "btrfs label"
        #    MyDiskMount = fs_related.BtrfsDiskMount
        extloop = MyDiskMount(fs_related.SparseLoopbackDisk(os_image, imgsize),
                                              extmnt,
                                              tfstype,
                                              4096,
                                              tlabel)
        try:
            extloop.mount()
        except MountError, e:
            extloop.cleanup()
            shutil.rmtree(extmnt, ignore_errors = True)
            imgloop.cleanup()
            shutil.rmtree(tmpoutdir, ignore_errors = True)
            shutil.rmtree(imgmnt, ignore_errors = True)
            raise CreatorError("Failed to loopback mount '%s' : %s" %(os_image, e))
        try:
            chroot.chroot(extmnt, None,  "/bin/env HOME=/root /bin/bash")
        except:
            print >> sys.stderr, "Failed to chroot to %s." % img
        finally:
            chroot.cleanup_after_chroot("img",extloop,None,None)
            return 1
        
    def do_pack(self):              
        def __mkinitrd(instance):
            kernelver = instance._get_kernel_versions().values()[0][0]
            args = [ "/usr/libexec/mkliveinitrd", "/boot/initrd-%s.img" % kernelver, "%s" % kernelver ]
            try:
                subprocess.call(args, preexec_fn = instance._chroot)
            except OSError, (err, msg):
               raise CreatorError("Failed to execute /usr/libexec/mkliveinitrd: %s" % msg)
                   
        def __run_post_cleanups(instance):
            kernelver = instance._get_kernel_versions().values()[0][0]
            args = ["rm", "-f", "/boot/initrd-%s.img" % kernelver]
            try:
                subprocess.call(args, preexec_fn = instance._chroot)
            except OSError, (err, msg):
               raise CreatorError("Failed to run post cleanups: %s" % msg)
               
        __mkinitrd(convertor)
        convertor._create_bootconfig()
        __run_post_cleanups(convertor)
        convertor.unmount()
        convertor.package()
        convertor.print_outimage_info()
            
    def do_unpack(self):
        convertoropts = configmgr.getConfigMgr().convert
        convertor = convertoropts["convertor"](convertoropts)        #consistent with destfmt
        srcimgsize = (misc.get_file_size(convertoropts["srcimg"])) * 1024L * 1024L
        convertor._set_fstype("ext3")
        convertor._set_image_size(srcimgsize)
        base_on = convertoropts["srcimg"]
        convertor.check_depend_tools()
        convertor.mount(base_on, None)
        return convertor

mic_plugin = ["livecd", LiveCDPlugin]
