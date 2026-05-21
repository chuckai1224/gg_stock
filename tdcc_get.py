# -*- coding: utf-8 -*-

import os
import sys
import inspect
from inspect import currentframe, getframeinfo
import tdcc_dist


def lno():
    cf = currentframe()
    filename = getframeinfo(cf).filename
    return '%s-L(%d)' % (os.path.basename(filename),
                         inspect.currentframe().f_back.f_lineno)


def main():
    # 從 TDCC 開放資料下載集保戶股權分散表,寫入 sql/tdcc_dist.db
    tdcc_dist.update_tdcc_from_opendata()


if __name__ == '__main__':
    main()
