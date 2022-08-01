"""
快捷部署模块，用于应对以下两种情况：

其一，需要批量解压服务器(patch)。该脚本可以将你zip批量解压到有序的文件夹中，
入你可以将weisheng.zip解压成weisheng0-99文件夹中。同时会将config/文件夹
同样也批量覆盖进去，从而实现如端口的变更。

其二，需要批量拷贝的情况(copy)，该脚本可以将源文件夹批量拷贝成有序的文件夹，
以便覆盖操作。

你可以使用 python server-patch.py 来直接查看用法，无需解读代码。
"""
import os
import sys
import time
import zipfile
import shutil


def del_old_zip(file_name):
    os.remove(file_name)


def unzip(file_path, root):
    # file_path 为zip文件的全路径
    # root 为解压后的路径
    zip_file = os.path.join(file_path)  # 拼接文件的全名
    if zip_file.endswith(".zip"):
        # 判断文件的结尾是否为zip结尾
        fz = zipfile.ZipFile(zip_file, "r")
        fileList = fz.namelist()
        size = len(fileList)
        progress = 0
        for file in fz.namelist():
            progress += 1
            if progress % 500 == 0:
                print(fr"【{root}】[", zip_file, " -> ", root, "] ", progress, "/", size, " about ",
                      (int)((progress / size) * 100),
                      "%")
            fz.extract(file, root)
        fz.close()
    else:
        print(fr"{zip_file} this is not zip")


def copyfile(f1path, f2path, value):
    f1 = open(f1path, 'r', encoding='UTF-8')
    f2 = open(f2path, 'w', encoding='UTF-8')
    content = f1.read()
    content = content.replace("%value%", str(value))

    vStr = str(value)
    if value < 10:
        vStr = "0" + vStr
    content = content.replace("%value2%", vStr)

    f2.write(content)
    f1.close()
    f2.close()
    return;


def copyDirWithValue(sourcePath, targetPath, value):
    if os.path.isdir(sourcePath):
        for file in os.listdir(sourcePath):
            copyDirWithValue(os.path.join(sourcePath, file), os.path.join(targetPath, file), value)
    else:
        if (not os.path.exists(targetPath)):
            return
        print(fr"【{value}】copy {sourcePath} >> {targetPath}")
        copyfile(sourcePath, targetPath, value)
    return


def runUnzipAndCoverConfig(zip_file, target_file, value):
    unzip(zip_file, target_file)
    copyDirWithValue(config_file, target_file, value)


def printHelp():
    print("请检查输入!")
    print("---------------------------------------------------------")
    print("该py用于快捷解压，替换，部署")
    print("usage: patch <zip压缩包> <配置文件> <解压文件夹(前缀)> <部署次数>")
    print("  >eg. patch weisheng.zip configs weisheng_ 10")
    print("usage: copy <源文件夹> <目标文件夹(前缀)> <复制次数>")
    print("  >eg. copy mld mld_ 10")
    print("---------------------------------------------------------")


if __name__ == "__main__":

    if len(sys.argv) <= 1 or sys.argv[1] == "?" or sys.argv[1] == "help":
        printHelp()
    elif sys.argv[1] == "patch" and len(sys.argv) >= 6:
        fileCurrent = os.path.dirname(os.path.abspath(__file__))
        zip_file = os.path.join(fileCurrent, sys.argv[2])
        config_file = os.path.join(fileCurrent, sys.argv[3])
        amount = int(sys.argv[5])
        timeBefore = time.time()
        print(fr"ready patch {zip_file} to {sys.argv[4]} in {amount} times")

        for i in range(amount):
            target_file = os.path.join(fileCurrent, sys.argv[4] + str(i))
            runUnzipAndCoverConfig(zip_file, target_file, i)
        timeCost = (time.time() - timeBefore)
        print(fr"ready patch {zip_file} to {sys.argv[4]} in {amount} times cost {timeCost}s")

    elif sys.argv[1] == "copy" and len(sys.argv) >= 5:
        fileCurrent = os.path.dirname(os.path.abspath(__file__))
        sourceFile = os.path.join(fileCurrent, sys.argv[2])
        amount = int(sys.argv[4])
        print(fr"ready copy {sourceFile} to {sys.argv[3]} in {amount} times")
        timeBefore = time.time()
        for i in range(amount):
            target_file = os.path.join(fileCurrent, sys.argv[3] + str(i))
            print(fr">正在复制 {target_file} {i}/{amount}")
            if os.path.exists(target_file):
                shutil.rmtree(target_file)
                print(fr">>！！删除原 {target_file} {i}/{amount}")
            shutil.copytree(sourceFile, target_file)
        timeCost = (time.time() - timeBefore)
        print(fr"copy {sourceFile} to {sys.argv[3]} in {amount} times cost {timeCost}s")
    else:
        printHelp()
