"""
该模块可以在服务器启动前执行，
其将从Mysql中读取一条路径，用于当作源文件夹，
并通过与当前路径地plugins文件夹进行MD5匹配，
若MD5不匹配，则将源文件夹中不匹配文件更新过来。

你可以使用 ython server-plugin-hotswap.py 来直接查看用法，无需解读代码。
"""

import os.path
import sys
import time
import hashlib
import shutil

import mysql.connector as sql


def info(msg):
    print("server-plugin-hotswap>", msg)


def infoWithoutEnd(msg):
    print("server-plugin-hotswap>", msg, end="")


# read md5 from file

def md5_file(filePath):
    md5 = None
    with open(filePath, 'rb') as fp:
        data = fp.read()
        md5 = hashlib.md5(data).hexdigest()
    return md5


def get_plugin_name(full_name):
    return full_name[0:len(full_name) - 4].replace(" ", "").split("-")[0]


def update_file_from_dir(source_dir, target_dir, source_to_target_dict):
    for key in source_to_target_dict.keys():
        timeBefore = time.time()
        value = source_to_target_dict[key]
        if os.path.exists(os.path.join(target_dir, key)):
            infoWithoutEnd(fr"--替换 {key} 为 {value} 中...")
            os.remove(os.path.join(target_dir, key))
        else:
            infoWithoutEnd(fr"--复制新增 {key} 中...")
        timeCost = (time.time() - timeBefore)
        print(fr"{timeCost}s!")
        shutil.copy(os.path.join(source_dir, value), os.path.join(target_dir, value))


def compare_and_copy_file(source_dir, target_dir):
    origin_source_plugins_map = {}
    valid_source_plugins_dict = {}

    need_to_hotswap_plugins = {}

    checked_plugin = []

    info(fr"正在汇总源插件中... [{source_dir}] ")
    for source_file in os.listdir(source_dir):
        # 如果是文件夹，跳转进入复制
        if os.path.isdir(source_file):
            info(fr"跳过目录{source_file}")
            # compare_and_copy_file(os.path.join(source_dir, source_file), os.path.join(target_dir, source_file))
        elif source_file.endswith(".jar"):
            pluginName = get_plugin_name(source_file)
            pluginMd5 = md5_file(os.path.join(source_dir, source_file))
            valid_source_plugins_dict[pluginName] = pluginMd5
            origin_source_plugins_map[pluginName] = source_file
            info(fr"--{source_file}> {pluginName}:{pluginMd5}")

    info(fr"正在比对目标插件中... [{target_dir}] ")
    for target_file in os.listdir(target_dir):
        if not os.path.isdir(target_file):
            if target_file.endswith(".jar"):
                pluginName = get_plugin_name(target_file)
                if pluginName not in valid_source_plugins_dict:
                    continue
                else:
                    checked_plugin.append(pluginName)
                    sourcePluginMd5 = valid_source_plugins_dict[pluginName]
                    pluginMd5 = md5_file(os.path.join(target_dir, target_file))

                    result = None
                    if sourcePluginMd5 == pluginMd5:
                        result = "最新版本！"
                    else:
                        result = "即将进行更新。。。"
                        need_to_hotswap_plugins[target_file] = origin_source_plugins_map[pluginName]

                    info(fr"--比对 {target_file}> {pluginName}:{pluginMd5} 结果> {result}")

    for key in valid_source_plugins_dict.keys():
        if key not in checked_plugin:
            info(fr"--未找到插件 {origin_source_plugins_map[key]}，即将复制更新。。。")
            need_to_hotswap_plugins[origin_source_plugins_map[key]] = origin_source_plugins_map[key]

    info("##########################################################################")
    info(fr"需要处理的文件数量 {len(need_to_hotswap_plugins)}")
    if len(need_to_hotswap_plugins) > 0:
        update_file_from_dir(source_dir, target_dir, need_to_hotswap_plugins)


def mysql_select_hotswap_path(raw_host, usr, pwd, database, table):
    resultPath = None
    try:
        mysqldb = sql.connect(
            host=raw_host,
            user=usr,
            password=pwd,
            database=database
        )
        cursor = mysqldb.cursor()
        cursor.execute(fr"select value from {table} where config='plugin_hotswap_path' limit 1;")
        result = cursor.next()
        if len(result) > 0:
            resultPath = result[0]
    except Exception as err:
        print(err)
    return resultPath


if __name__ == '__main__':
    if len(sys.argv) < 4:
        info("参数有误!")
        info(fr"usage: {os.path.basename(__file__)} <数据库连接> <账号> <密码>")
    else:
        info("即将进行热更新,正在准备数据中...")
        timeBefore = time.time()

        mysql_host = sys.argv[1]
        mysql_usr = sys.argv[2]
        mysql_pwd = sys.argv[3]
        if mysql_pwd == '@':
            mysql_pwd = ''
        mysql_database = 'liuweipladugin'
        mysql_table = 'global_config'

        '''从数据库读取文件'''
        info("##########################################################################")
        infoWithoutEnd("正在与数据库连接并读取路径...")

        # 热更新目录，源目录
        hotswap_path = mysql_select_hotswap_path(mysql_host, mysql_usr, mysql_pwd, mysql_database, mysql_table)

        if hotswap_path is None:
            hotswap_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hotswap_plugins")
            info(f"转为使用默认路径{hotswap_path}")
        else:
            print(fr"{hotswap_path}")

        # 目标目录
        plugin_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugins")

        paths = [hotswap_path, plugin_path]
        # 检测并创建目录
        for path in paths:
            if not os.path.exists(path):
                os.mkdir(path)
                info(fr"目录【{path}】不存在，已创建！")

        '''比对并复制'''
        info("##########################################################################")
        info(fr"正在进行热更新检查中 源》{hotswap_path} 目标》{plugin_path}")
        compare_and_copy_file(hotswap_path, plugin_path)
        info("##########################################################################")

        timeCost = (time.time() - timeBefore)
        info(fr"热更新结束,耗时 {timeCost} 秒")
