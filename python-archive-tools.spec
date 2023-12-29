%bcond_without tests
%global distname archive-tools

%if 0%{?sle_version} >= 150500
%global pythons python3 python311
%else
%{?!python_module:%define python_module() python3-%{**}}
%define skip_python2 1
%endif

Name:		python-%{distname}
Version:	$version
Release:	0
Summary:	$description
License:	Apache-2.0
URL:		$url
Group:		Development/Libraries/Python
Source:		https://github.com/RKrahl/archive-tools/releases/download/%{version}/%{distname}-%{version}.tar.gz
BuildRequires:	%{python_module base >= 3.6}
BuildRequires:	%{python_module setuptools}
BuildRequires:	fdupes
BuildRequires:	python-rpm-macros
%if %{with tests}
BuildRequires:	%{python_module PyYAML}
BuildRequires:	%{python_module lark-parser}
BuildRequires:	%{python_module distutils-pytest}
BuildRequires:	%{python_module packaging}
BuildRequires:	%{python_module pytest >= 3.0}
BuildRequires:	%{python_module pytest-dependency >= 0.2}
BuildRequires:	%{python_module python-dateutil}
%endif
Requires:	python-PyYAML
Requires:	python-lark-parser
Requires:	python-packaging
Recommends:	python-IMAPClient
Recommends:	python-python-dateutil
BuildArch:	noarch
%python_subpackages

%description
$long_description


%prep
%setup -q -n %{distname}-%{version}


%build
%python_build


%install
%python_install
for f in `ls %{buildroot}%{_bindir}`
do
    mv %{buildroot}%{_bindir}/$$f %{buildroot}%{_bindir}/$${f%%.py}
done
%fdupes %{buildroot}%{python_sitelib}


%if %{with tests}
%check
%python_expand $$python setup.py test
%endif


%files %{python_files}
%license LICENSE.txt
%doc README.rst CHANGES.rst
%config(noreplace) %{_sysconfdir}/backup.cfg
%{python_sitelib}/*
%{_bindir}/*


%changelog
