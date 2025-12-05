@echo off
:: Helper script for setting up development environment
:: Use with care, you may need to install the package first and then 
:: remove the targets that are replaced by links below before running 
:: this script.
:: Also - when uninstalling the package, FME may wipe the folders we 
:: are linking to here.
setlocal
if not defined fme_build (
    set /p fme_build=FME Build Tag, example 24820-win64: 
)
if not defined package_qname (
    set /p package_qname=Package Qualified Name, syntax publisher_uid.package_uid: 
)
set packages_dir=%appdata%\Safe Software\FME\Packages\%fme_build%
set python_dir=%packages_dir%\python\%package_qname%

if not defined py_package_qname (
    set /p py_package_qname=Python Package Name: 
)
pushd "%~dp0"

mklink /j "%python_dir%\%py_package_qname%" "python\%py_package_qname%\src\%py_package_qname%"

set transformers_dir=%packages_dir%\transformers
mklink /j "%transformers_dir%\%package_qname%" transformers

popd
endlocal
echo on