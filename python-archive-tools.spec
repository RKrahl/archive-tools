%bcond_with tests

Name:		python3-archive-tools
Version:	$version
Release:	0
Url:		$url
Summary:	$description
License:	Apache-2.0
Group:		Development/Libraries/Python
Source:		archive-tools-%{version}.tar.gz
BuildRequires:	python3-base >= 3.4
%if %{with tests}
BuildRequires:	python3-PyYAML
BuildRequires:	python3-distutils-pytest
BuildRequires:	python3-pytest-dependency >= 0.2
BuildRequires:	python3-pytest >= 3.0
%endif
Requires:	python3-PyYAML
Recommends:	python3-IMAPClient
Recommends:	python3-python-dateutil
BuildArch:	noarch
BuildRoot:	%{_tmppath}/%{name}-%{version}-build

%description
$long_description

%prep
%setup -q -n archive-tools-%{version}

%build
python3 setup.py build

%install
python3 setup.py install --optimize=1 --prefix=%{_prefix} --root=%{buildroot}
for f in `ls %{buildroot}%{_bindir}`
do
    mv %{buildroot}%{_bindir}/$$f %{buildroot}%{_bindir}/$${f%%.py}
done

%if %{with tests}
%check
python3 setup.py test
%endif

%files 
%defattr(-,root,root)
%doc README.rst
%{python3_sitelib}/*
%{_bindir}/*

%changelog
