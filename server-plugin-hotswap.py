# -*- coding: utf-8 -*-
r"""
该模块可以在服务器启动前执行，
其将从Mysql中读取一条路径，用于当作源文件夹，
并通过与当前路径的plugins/中插件进行MD5匹配，
若MD5不匹配，则将源文件夹中不匹配文件更新过来。

-----------------------------------------------------------

使用该功能你需要遵守的规则：
一、插件匹配规则，如Abcd-123.jar与Abcd-321.jar会被认为是同一个插件，只看'-'前边的名字，如果没有'-'，则看全部。
二、插件将以MD5进行匹配，请时刻保证源文件夹中的插件为最新版本。

注意，你需要提前准备好数据库以使用该脚本：
数据库表格式：
{
    config TINYTEXT,
    value TINYTEXT
}
数据库配置：
{
    config = plugin_hotswap_path,
    value = 你的路径(如D:\hotswap_plugins)
}

你可以使用 python server-plugin-hotswap.py 来直接查看用法，无需解读代码。
"""

import os.path
import sys
import time
import hashlib
import shutil
import re
from colorama import Fore

import mysql.connector as sql


def info(msg):
    print("server-plugin-hotswap>", msg, Fore.RESET)


def infoWithoutEnd(msg):
    print("server-plugin-hotswap>", msg, Fore.RESET, end="")

def check_file_type(file_name):
    return file_name.endswith(".jar") or file_name.endswith(".yml") or file_name.endswith(".json")

# read md5 from file
def md5_file(filePath):
    md5 = None
    with open(filePath, 'rb') as fp:
        data = fp.read()
        md5 = hashlib.md5(data).hexdigest()
    return md5


def get_plugin_name(full_name):
    return re.split('[-|_]', full_name[0:full_name.rindex(".")])[0]


def update_file_from_dir(source_dir, target_dir, source_to_target_dict):
    for key in source_to_target_dict.keys():
        timeBefore = time.time()
        value = source_to_target_dict[key]
        if os.path.exists(os.path.join(target_dir, key)):
            infoWithoutEnd(Fore.RED + fr"[!] --替换 {key} 为 {value} 中...")
            os.remove(os.path.join(target_dir, key))
        else:
            infoWithoutEnd(Fore.RED + fr"[!] --复制新增 {key} 中...")
        timeCost = (time.time() - timeBefore)
        print(fr"{timeCost}s!")
        shutil.copy(os.path.join(source_dir, value), os.path.join(target_dir, value))


def compare_and_copy_file(source_dir, target_dir):
    '''
    比较两个目录，并且复制需要更新的类型

    :param source_dir: 源文件夹
    :param target_dir: 目标文件夹
    '''
    origin_source_plugins_map = {}
    valid_source_plugins_dict = {}

    need_to_hotswap_plugins = {}

    checked_plugin = []

    # info(fr"正在汇总源插件中... [{source_dir}] ")
    for source_file in os.listdir(source_dir):
        # 如果是文件夹，跳转进入复制
        if os.path.isdir(source_file):
            compare_and_copy_file(os.path.join(source_dir, source_file), os.path.join(target_dir, source_file))
            # info(Fore.YELLOW + fr"-------------------------------------{source_file}-------------------------------------" + Fore.RESET)
        elif check_file_type(source_file):
            pluginName = get_plugin_name(source_file)
            pluginMd5 = md5_file(os.path.join(source_dir, source_file))
            valid_source_plugins_dict[pluginName] = pluginMd5
            origin_source_plugins_map[pluginName] = source_file
            # info(fr"*--{source_file}> {pluginName}:{pluginMd5}")

    # info(Fore.GREEN + fr"@正在比对目标插件中... [{target_dir}] " + Fore.RESET)
    for target_file in os.listdir(target_dir):
        if not os.path.isdir(target_file):
            if check_file_type(target_file):
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

                    info(Fore.GREEN + fr"@--比对 {target_file}> {pluginName} of {pluginMd5} 结果> {result}")

    for key in valid_source_plugins_dict.keys():
        if key not in checked_plugin:
            info(Fore.GREEN + fr"@--未找到文件 {origin_source_plugins_map[key]}，即将复制更新。。。")
            need_to_hotswap_plugins[origin_source_plugins_map[key]] = origin_source_plugins_map[key]

    # info("##########################################################################")
    info(Fore.YELLOW + fr"@[{target_dir}] 需要处理的文件数量 {len(need_to_hotswap_plugins)}")
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
    # 检测参数长度是否合适,如果合适才进行下一步
    if len(sys.argv) < 6:
        info(Fore.BLUE + "参数有误!")
        info(fr"usage: {os.path.basename(__file__)} <host> <database> <table> <账号> <密码> - 注意，数据库需提前创建并配置。")
    else:
        info(Fore.BLUE + "即将进行热更新,正在准备数据中...")
        timeBefore = time.time()

        # 加载初始数据
        mysql_host = sys.argv[1]
        mysql_usr = sys.argv[4]
        mysql_pwd = sys.argv[5]
        if mysql_pwd == '@':
            mysql_pwd = ''
        mysql_database = sys.argv[2]
        mysql_table = sys.argv[3]

        # 从数据库读取路径
        '''从数据库读取文件'''
        info(Fore.CYAN + "##########################################################################")
        infoWithoutEnd(Fore.BLUE + "正在与数据库连接并读取路径...")

        # 热更新目录，源目录，
        hotswap_source_path = mysql_select_hotswap_path(mysql_host, mysql_usr, mysql_pwd, mysql_database, mysql_table)

        if hotswap_source_path is None:
            hotswap_source_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hotswap_dir")
            info(Fore.BLUE + f"转为使用默认路径{hotswap_source_path}")
        else:
            print(fr"{hotswap_source_path}")

        # 目标目录
        # target_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugins")
        target_path = os.path.dirname(os.path.abspath(__file__))

        paths = [hotswap_source_path, target_path]
        # 检测并创建目录
        for path in paths:
            if not os.path.exists(path):
                os.mkdir(path)
                info(Fore.BLUE + fr"目录【{path}】不存在，已创建！")

        '''比对并复制'''
        info(Fore.CYAN + "##########################################################################")
        info(Fore.BLUE + fr"正在进行热更新检查中 源》{hotswap_source_path} 目标》{target_path}")
        compare_and_copy_file(hotswap_source_path, target_path)
        info(Fore.CYAN + "##########################################################################")

        timeCost = (time.time() - timeBefore)
        info(Fore.BLUE + fr"热更新结束,耗时 {timeCost} 秒")
