#!/bin/bash

tar czvf graphite-dependencies.tgz linux_2_6_32 boost_1_38_0
scp graphite-dependencies.tgz intel@vtuin:~/mirror/

./tools/makepythondist.sh
