# find script directory
folder="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# create .c and .so
python compile_dtw.py build_ext --build-lib $folder/ --build-temp $folder/tmp/

# clean-up temp
rm -Rf $folder/tmp/