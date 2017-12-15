#!/usr/bin/env python
# coding=utf-8

import sys, os 
import MySQLdb as mysql
import json
import hashlib

sys.path.insert(1, os.path.join(sys.path[0], '..'))
from nbNet.nbNetFramework import nbNet
from dbutil.dbutil import DB

monTables = [
    'stat_0',
    'stat_1',
    'stat_2',
    'stat_3',
]

db = DB(host="localhost", mysql_user="reboot", mysql_pass="reboot123", \
                mysql_db="falcon")

def fnvhash(string):
    ret = 97
    for i in string:
        ret = ret ^ ord(i) * 13
    return ret

def insertMonData(d_in):
    try:
        j = {}
        data = json.loads(d_in)
        print data
        dTime = int(data['Time'])
        hostIndex = monTables[fnvhash(data['Host']) % len(monTables)]
        for ud in data:
            if ud.startswith('UD_'):
                j[ud] = data[ud]
        ud_data = json.dumps(j)
        sql = "INSERT INTO `%s` (`host`,`mem_free`,`mem_usage`,`mem_total`,`load_avg`,`time`,`user_define`) VALUES('%s', '%d', '%d', '%d', '%s', '%d','%s')" % \
            (hostIndex, data['Host'], data['MemFree'], data['MemUsage'], data['MemTotal'], data['LoadAvg'], dTime,ud_data)
        c = db.execute(sql)
        ## 把UD_开头的监控项数据json插入到user_define数据表中
    except mysql.IntegrityError:
        pass
    

if __name__ == '__main__':
    def logic(d_in):
        insertMonData(d_in)
#        print d_in
        return("OK")

    saverD = nbNet('0.0.0.0', 50001, logic)
    saverD.run()


