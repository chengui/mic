%define is_tizen %(test -e /etc/tizen-release -o -e /etc/meego-release && echo 1 || echo 0)
%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
Name:       mic
Summary:    Image Creator for Linux Distributions
Version:    0.15
Release:    1
Group:      System/Base
License:    GPLv2
BuildArch:  noarch
URL:        http://www.tizen.org
Source0:    %{name}_%{version}.tar.gz
Requires:   rpm-python
Requires:   util-linux
Requires:   coreutils
Requires:   python >= 2.5
Requires:   e2fsprogs
Requires:   dosfstools >= 2.11-8
Requires:   syslinux >= 3.82
Requires:   kpartx
Requires:   parted
Requires:   device-mapper
Requires:   /usr/bin/genisoimage
Requires:   cpio
Requires:   isomd5sum
Requires:   gzip
Requires:   bzip2
Requires:   squashfs-tools >= 4.0
Requires:   qemu-arm-static
Requires:   python-urlgrabber
%if 0%{is_tizen} == 0
Requires:   yum >= 3.2.24
%endif
%if 0%{?suse_version}
Requires:   btrfsprogs
%else
Requires:   btrfs-progs
%endif

%if 0%{?fedora_version} || 0%{is_tizen} == 1
Requires:   m2crypto
%else
%if 0%{?suse_version} == 1210
Requires:   python-M2Crypto
%else
Requires:   python-m2crypto
%endif
%endif

%if 0%{?fedora_version} > 13 || 0%{is_tizen} == 1
Requires:   syslinux-extlinux
%endif

Requires:   python-zypp

BuildRequires:  python-devel
BuildRequires:  python-docutils

Obsoletes:  mic2

BuildRoot:  %{_tmppath}/%{name}_%{version}-build


%description
The tool mic is used to create and manipulate images for Linux distributions.
It is composed of three subcommand\: create, convert, chroot. Subcommand create
is used to create images with different types; subcommand convert is used to
convert an image to a specified type; subcommand chroot is used to chroot into
an image.


%prep
%setup -q -n %{name}-%{version}

%build
CFLAGS="$RPM_OPT_FLAGS" %{__python} setup.py build
make man

%install
rm -rf $RPM_BUILD_ROOT
%if 0%{?suse_version}
%{__python} setup.py install --root=$RPM_BUILD_ROOT --prefix=%{_prefix}
%else
%{__python} setup.py install --root=$RPM_BUILD_ROOT -O1
%endif

# remove yum backend for tizen
%if 0%{is_tizen} == 1
rm -rf %{buildroot}/%{_prefix}/lib/%{name}/plugins/backend/yumpkgmgr.py
rm -rf %{buildroot}/%{_sysconfdir}/%{name}/bootstrap.conf
%endif

# install man page
mkdir -p %{buildroot}/%{_prefix}/share/man/man1
install -m644 mic.1 %{buildroot}/%{_prefix}/share/man/man1

%files
%defattr(-,root,root,-)
%doc README.rst
%doc doc/RELEASE_NOTES
%{_mandir}/man1/*
%dir %{_sysconfdir}/%{name}
%config(noreplace) %{_sysconfdir}/%{name}/%{name}.conf
%if 0%{is_tizen} == 0
%config %{_sysconfdir}/%{name}/bootstrap.conf
%endif
%{python_sitelib}/*
%dir %{_prefix}/lib/%{name}
%{_prefix}/lib/%{name}/*
%{_bindir}/*