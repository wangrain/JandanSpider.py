__author__ = 'Rain.wang'
import os
import logging
import logging.config
import fileinput
import requests
import datetime
logging.config.fileConfig("./log.conf")
# create logger
logger_name = "example"
logger = logging.getLogger(logger_name)


def del_repeat_img(imgId, new_filename, filelist, folder):
    repeat_list = []
    result = 0
    #从文件名列表中找出同一ID的文件
    for filename in filelist:
        if filename.split("_").pop().split(".")[0] == imgId:
            targetFile = os.path.join(folder, filename)
            repeat_list.append(targetFile)
    #删除或重命名ID重复的文件
    for n in range(len(repeat_list)):
        if n != len(repeat_list) - 1:
            logger.debug('---删除---' + os.path.basename(repeat_list[n]) + '---')
            os.remove(repeat_list[n])
            result = 1
        else:
            if repeat_list[n].find(new_filename) == -1:
                logger.debug('---重命名---' + os.path.basename(repeat_list[n]) + '的为' + new_filename + '---')
                os.rename(repeat_list[n], new_filename)
            else:
                logger.debug('---跳过---' + os.path.basename(repeat_list[n]) + '---')
            result = 1
    return result


def save_imgs(folder, img_name, img_url):
    filelist = os.listdir(folder)
    # 删除/重命名id重复的图片
    img_id = img_name.split("_").pop().split(".")[0]
    result = del_repeat_img(img_id, img_name, filelist, folder)
    if (result == 0) & (img_url != ''):
        try:
            if requests.head(img_url).status_code == 200:
                image = requests.get(img_url, timeout=100)
                with open(img_name, 'wb') as f:
                    f.write(image.content)
                    f.close()
        except Exception as e:
            logger.error('=============下载异常-start============')
            logger.error('下载异常---' + img_url + '---' + img_name + '---')
            logger.error(e)
            logger.error('=============下载异常-over============')
            return 0
        # 下载成功
        logger.info('---下载成功---' + img_url + '---' + img_name + '---')


def downloadImage(folder, list_file):
    # 获取当前工作目录
    folder_top = os.getcwd()
    folder = folder_top + '\\' + folder
    # 判断目录是否存在，若存在，则删除该目录及目录内所有内容
    if os.path.exists(folder):
        logger.info('已存在文件夹folder，将更新该文件夹下图片')
    else:
        os.mkdir(folder)
    os.chdir(folder)

    # 开始读取列表文件
    list_file = '..\\' + list_file
    if not os.path.isfile(list_file):
        logger.error("未找到列表文件[" + list_file + "]")
        return 0
    reader = fileinput.input([list_file])
    logger.info("开始遍历列表文件[" + list_file + "]")
    for line in reader:
        tmp = line.split("|")
        img_name = tmp[0]
        img_url = tmp[1]
        save_imgs(folder, img_name, img_url)
    reader.close()


if __name__ == '__main__':
    # folder = input("请输入文件夹名称(默认名 'ooxx'): ")
    # list_file = input("请输入列表文件名称(默认为 'url_list.txt'): ")
    folder = ""
    list_file = ""
    # 默认文件夹为，本程序当前文件夹下'ooxx'文件夹
    if folder == "":
        folder = 'ooxx'
    if list_file == "":
        list_file = 'url_list.txt'
    starttime = datetime.datetime.now()
    downloadImage(str(folder), str(list_file))
    endtime = datetime.datetime.now()
    print('运行时间：' + str((endtime - starttime).seconds) + '秒')
