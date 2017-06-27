__author__ = 'Rain.wang'
import urllib.request
import requests
import os
import re
import shutil
import logging
import logging.config
logging.config.fileConfig("./log.conf")
# create logger
logger_name = "example"
logger = logging.getLogger(logger_name)

DATE=20130101
FLAG=0

class ImgObj:
	imgId=''
	imgUrl=''
	imgOO=0
	imgXX=0
	def __init__(self, imgId, imgUrl,imgOO,imgXX,imgPage):
		self.imgId = imgId
		self.imgUrl = imgUrl
		self.imgOO = imgOO
		self.imgXX = imgXX
		self.imgPage = imgPage
	

def url_open(url):
	global DATE,FLAG
	FLAG += 1
	#通过循环增加FLAG，避开403 forbidden
	if FLAG == 10:
		DATE += 1
		FLAG = 0
	head_browser = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:23.0) Gecko/'+str(DATE)+' Firefox/23.0'
	#增加gif-click-load=off的参数，用于下载gif动态图(亲测无效)
	head_params = '_gat=1; nsfw-click-load=off; gif-click-load=on; _ga=GA1.2.1861846600.1423061484'
	#大括号为字典，用法为dic={'a':12,'b':34}
	headers = {'User-Agent':head_browser,'Cookie':head_params}
	req = urllib.request.Request(url=url, headers=headers)
	return urllib.request.urlopen(req).read()

def get_page(url):
	html = url_open(url).decode('utf8')
	pattern = r'<span class="current-comment-page">\[(\d{4})\]</span>' #正则表达式寻找页面地址
	page = int(re.findall(pattern,html)[0])
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
				img_oo = i.split('<span id="cos_support-'+img_id+'">',2)[1].split('<',2)[0]
				img_xx = i.split('<span id="cos_unsupport-'+img_id+'">',2)[1].split('<',2)[0]
				#跳过oo小于100，或xx大于oo的图片
				if (int(img_oo) < 100) | (int(img_xx) > int(img_oo)):
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
						else :
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
						else :
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
					logger.debug('---获取图片---'+img_url)
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

def del_repeat_img(imgId,new_filename,filelist,folder):
	repeat_list = []
	result = 0
	for num in range(len(filelist)):
		filename=filelist[num]
		if filename.find(imgId) != -1:
			targetFile = os.path.join(folder,filename)
			repeat_list.append(targetFile)
	if len(repeat_list)>1:
		#超过1个重复ID
		for n in range(len(repeat_list)):
			if n != len(repeat_list)-1:
				logger.debug('---删除---'+os.path.basename(repeat_list[n])+'---')
				os.remove(repeat_list[n])
				result = 1
			else:
				if repeat_list[n].find(new_filename) == -1:
					logger.debug('---重命名---'+os.path.basename(repeat_list[n])+'的为'+new_filename+'---')
					os.rename(repeat_list[n], new_filename)
				else:
					logger.debug('---跳过---'+os.path.basename(repeat_list[n])+'---')
				result = 1
	elif len(repeat_list)==1:
		#仅有一个图片ID重复
		if repeat_list[0].find(new_filename) == -1:
			logger.debug('---重命名---'+os.path.basename(repeat_list[0])+'的为'+new_filename+'---')
			os.rename(repeat_list[0], new_filename)
		else:
			logger.debug('---跳过---'+os.path.basename(repeat_list[0])+'---')
		result = 1
	else:
		return 0
	return result
			
		

def save_imgs(imgObj_list,page_num,folder):
	filelist = os.listdir(folder)
	for i in imgObj_list:
		#由于个别图片没有后缀，故先用/分割，然后用.分割，如果用.分割后列表长度为1，则默认后缀为.jpg
		postfix_list = i.imgUrl.split('/')[-1].split('.')
		if len(postfix_list) == 1:
			postfix = 'jpg'
		else:
			postfix = postfix_list[-1]
		#文件名为oo数_xx数_page页数_ID号，例如：oo89_xx89_1601-11211.jpg
		filename = 'oo'+i.imgOO+'_xx'+i.imgXX+'_page'+str(i.imgPage)+'_'+i.imgId+'.'+postfix
		#删除/重命名id重复的图片
		result = del_repeat_img(i.imgId,filename,filelist,folder)
		if (result == 0) & (i.imgUrl != ''):
			try:
				#image = url_open(i.imgUrl)
				image = requests.get(i.imgUrl,timeout=100)
				with open(filename,'wb') as f:
					f.write(image.content)
					f.close()
			except Exception as e:
				logger.error('=============下载异常-start============')
				logger.error('下载异常---'+i.imgUrl+'---'+filename+'---')
				logger.error(e)
				logger.error('=============下载异常-over============')
				continue
			#下载成功
			logger.info('---下载成功---'+i.imgUrl+'---'+filename+'---')

def download_mm(folder,pages,page_num):
	#获取当前工作目录
	folder_top = os.getcwd()
	folder = folder_top + '\\' + folder
	#判断目录是否存在，若存在，则删除该目录及目录内所有内容
	if os.path.exists(folder):
		logger.info('已存在文件夹folder，将更新该文件夹下图片')
	else:
		os.mkdir(folder)
	#跳转到文件夹
	os.chdir(folder)
	url = 'http://jandan.net/ooxx/'
	if page_num == 0:
		#获取网页最新的地址
		page_num = get_page(url)
	while page_num != 0:
		#组合网页地址
		page_url = url + 'page-' + str(page_num) + '#comments'
		#获取图片地址
		imgObj_list = get_ImgObjs(page_url,page_num)
		if imgObj_list == 0:
			logger.info('就看到这里吧~')
			return 0
		#保存图片
		save_imgs(imgObj_list,page_num,folder)
		logger.info(page_url+'-------------finish')
		#递减下个网页
		page_num -= 1
		pages -= 1
		if pages == 0:
			return 0
		

if __name__ == '__main__':
	folder = input("请输入文件夹名称(默认名 'ooxx'): " )
	pages = input("您想爬取多少页(默认为全部下载): ")
	page_num = input("您想从第几页开始下载（默认从最新一页开始）: ")
	#默认文件夹为，本程序当前文件夹下'ooxx'文件夹
	if folder=="":
		folder = 'ooxx'
	if pages=="":
		pages = 0
	if page_num=="":
		page_num = 0
	download_mm(str(folder),int(pages),int(page_num))
	logger.info('下载完毕!')
