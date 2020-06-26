#!/bin/bash

make clean
schroot --preserve-environment --chroot=lenny make

tar czf graphite-deps-lenny.tgz config/ include/
scp graphite-deps-lenny.tgz intel@vtuin:~/mirror/

