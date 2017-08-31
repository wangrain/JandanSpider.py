__author__ = 'Rain.wang'
import urllib.request
import requests
import os
import re
import shutil
import logging
import logging.config
import fileinput
import datetime
logging.config.fileConfig("./log.conf")
# create logger
logger_name = "example"
logger = logging.getLogger(logger_name)

DATE=20130101
FLAG=0
MIN_OO=500
MAX_XX=MIN_OO + 100

class ImgObj:
    imgId = ''
    imgUrl = ''
    imgOO = 0
    imgXX = 0
    imgName = ''
    imgPage = 0
    def __init__(self, imgId, imgUrl, imgOO, imgXX, imgPage):
        self.imgId = imgId
        self.imgUrl = imgUrl
        self.imgOO = imgOO
        self.imgXX = imgXX
        self.imgPage = imgPage
        #由于个别图片没有后缀，故先用/分割，然后用.分割，如果用.分割后列表长度为1，则默认后缀为.jpg
        postfix_list = imgUrl.split('/')[-1].split('.')
        if len(postfix_list) == 1:
            postfix = 'jpg'
        else:
            postfix = postfix_list[-1]
        #文件名为oo数_xx数_page页数_ID号，例如：oo89_xx89_page1601_11211.jpg
        self.imgName = 'oo'+str(imgOO)+'_xx'+str(imgXX)+'_page'+str(imgPage)+'_'+imgId+'.'+postfix

def url_open(url):
    global DATE, FLAG
    FLAG += 1
    #通过循环增加FLAG，避开403 forbidden
    if FLAG == 10:
        DATE += 1
        FLAG = 0
    head_browser = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/'+str(DATE)+' Firefox/23.0'
    #增加gif-click-load=off的参数，用于下载gif动态图(亲测无效)
    head_params = '_gat=1; nsfw-click-load=off; gif-click-load=on; _ga=GA1.2.1861846600.1423061484'
    #大括号为字典，用法为dic={'a':12,'b':34}
    headers = {'User-Agent': head_browser, 'Cookie': head_params}
    req = urllib.request.Request(url=url, headers=headers)
    return urllib.request.urlopen(req).read()

def get_page(url):
    html = url_open(url).decode('utf8')
    pattern = r'<span class="current-comment-page">\[(\d{0,9})\]</span>' #正则表达式寻找页面地址
    page = int(re.findall(pattern, html)[0])
    return page

def get_ImgObjs(page_url,page_num):
    html = url_open(page_url).decode('utf8')
    html = html.replace('\n','')
    html = html.replace('\t','')
    li_list = html.split('<li id="comment-')
    imgObj_list=[]
    if len(li_list)>1:
        del li_list[0]
        del li_list[-1]
        for i in li_list:
            try:
                img_id = i.split('\"')[0]
                pattern = r'\[<span>(\d{0,9})</span>\]' #正则表达式寻找oo和xx数
                img_oo = int(re.findall(pattern, i)[0])
                img_xx = int(re.findall(pattern, i)[1])
                #跳过oo小于MIN_OO，或xx大于MAX_XX的图片
                if (int(img_oo) < MIN_OO) | (int(img_xx) > MAX_XX):
                    continue
                #找到图片列表:包括<img>和<a>
                img_list = i.split('<div class="text">',2)[1].split('<p',2)[1].split('</p>',2)[0].split('<br>')
                img_name_list=[]
                count = 0
                for img in img_list:
                    if img.find('<a') != -1:
                        img_url = img.partition('href="')[2].split('"')[0]
                        #若一个帖子中有多张图，则排除文件名一样的
                        img_name = img_url.split('/')[len(img_url.split('/'))-1]
                        if img_name not in img_name_list:
                            img_name_list.append(img_name)
                        else:
                            continue
                    elif img.find('<img src="') != -1:
                        img = img.split('<img',2)[1].split('>',2)[0]
                        if(img.find('gif') != -1 & img.find('org_src') != -1):
                            img_url = img.partition('org_src="')[2].split('"')[0]
                        else:
                            img_url = img.partition('src="')[2].split('"')[0]
                        #若一个帖子中有多张图，则排除文件名一样的
                        img_name = img_url.split('/')[len(img_url.split('/'))-1]
                        if img_name not in img_name_list:
                            img_name_list.append(img_name)
                        else:
                            continue
                    else:
                        logger.error('异常图片源(page='+str(page_num)+',id='+img_id+')----'+img)
                        continue
                    #给图片地址添加http头
                    if img_url.startswith('//'):
                        img_url = 'http:' + img_url
                    if img_url == '':
                        logger.error('异常图片源(page='+str(page_num)+',id='+img_id+')----'+img)
                        continue
                    #一个帖子等多张图片时命名
                    if(count != 0):
                        img_id = img_id + '_' + str(count)
                    # logger.debug('---获取图片---'+img_url)
                    imgObj_list.append(ImgObj(img_id,img_url,img_oo,img_xx,page_num))
                    count += 1
            except Exception as e:
                logger.error('=============img_url解析异常(page='+str(page_num)+',id='+img_id+')-start============')
                logger.error(img+'\n')
                logger.error(e)
                logger.error('=============img_url解析异常-over============')
                continue
    elif html.find('<h3 class="title">就看到这里了。</h3>') != -1:
        return 0
    else:
        logger.error('无法读取正常页面，li_list长度为'+str(len(li_list)))
        return 0
    return imgObj_list

#将图片名和url信息写入文件中
def save_urls(img_dict,list_file):
    logger.info("开始写入文件")
    #遍历字典，判断url是否可用，保存可用url
    line_w = ""
    for img_tuple in img_dict.items():
        url = img_tuple[0].strip()
        file_name = img_tuple[1]
        try :
            response = requests.head(url)
        except Exception as e :
            logger.error("访问图片URL异常"+url)
            logger.error(e)
            continue
        if response.status_code == 200:
            # logger.debug("url["+url+"]-------可用")
            #行存储方式为 fileName|url
            line_w = line_w + file_name + '|' + url +'\n'
        else:
            logger.debug("url["+url+"]-------不可用")
    #将更新后的列表，存入文件中
    writer = open(list_file, 'wt')
    writer.write(line_w)


#获取出所有图片对象列表
def get_ImgDict(list_file,pages,page_num):
    #读取当前列表文件，取出文件名和URL
    img_dict = {}
    if os.path.isfile(list_file):
        logger.info("开始读取原列表文件"+list_file)
        reader = fileinput.input([list_file])
        for line_r in reader :
            img_info = line_r.split("|") #行存储方式为 fileName|url
            img_dict[img_info[1]] = img_info[0] #以url为键，fileName为值避免重复
        reader.close()
        logger.info("读取列表文件完毕，开始获取url")

    url = 'http://jandan.net/ooxx/'
    if page_num == 0:
        #获取网页最新的地址
        page_num = get_page(url)
    while page_num != 0:
        #组合网页地址
        page_url = url + 'page-' + str(page_num) + '#comments'
        #获取图片地址列表
        imgObj_list = get_ImgObjs(page_url,page_num)
        #将本页url列表合并到img_dict中
        for imgObj in imgObj_list:
            if img_dict.get(imgObj.imgUrl) is None:
                img_dict[imgObj.imgUrl] = imgObj.imgName
            else:
                #若原文件列表中存在该url，则对比oo数判断是否更新文件名，保留oo数更多的文件名
                old_oo = img_dict[imgObj.imgUrl].split("_")[0].split("oo")[1]
                if int(imgObj.imgOO) > int(old_oo):
                    img_dict[imgObj.imgUrl] = imgObj.imgName
        if imgObj_list == 0:
            logger.info('就看到这里吧~')
            return img_dict
        logger.info(page_url+'-------------finish')
        #递减下个网页
        page_num -= 1
        pages -= 1
        #pages降为0时返回
        if pages == 0:
            logger.info("url获取完毕")
            return img_dict
    #page_num降为0时返回
    logger.info("url获取完毕")
    return img_dict

if __name__ == '__main__':
    list_file=""
    pages=0
    page_num=0
    list_file = input("请输入列表文件名称(默认名 'url_list.txt'): " )
    pages = input("您想爬取多少页(默认为全部下载): ")
    page_num = input("您想从第几页开始下载（默认从最新一页开始）: ")
    if list_file=="":
        list_file = "url_list.txt"
    if pages=="":
        pages = 0
    if page_num=="":
        page_num = 0
    #获取图片对象列表
    starttime = datetime.datetime.now()
    img_dict = get_ImgDict(list_file,int(pages),int(page_num))
    save_urls(img_dict,list_file)
    logger.info('保存完毕!')
    endtime = datetime.datetime.now()
    print('运行时间：' + str((endtime - starttime).seconds) + '秒')
