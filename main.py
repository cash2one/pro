#!/usr/bin/python
# encoding=utf-8
import time, datetime
import web
import urllib2, urllib
import json
import lxml
from lxml import etree
import time
from WXBizMsgCrypt import WXBizMsgCrypt
from peewee import *
from peewee import Expression
import string
# Thread
import thread

# DEBUG Options
import logging
from logging.handlers import RotatingFileHandler

#log_formatter = logging.Formatter('%(asctime)s %(levelname)s %(funcName)s(%(lineno)d) %(message)s')
#logFile = './log/log'
#my_handler = RotatingFileHandler(logFile, mode='a', maxBytes=5*1024, backupCount=2, encoding=None, delay=0)
#my_handler.setFormatter(log_formatter)
#my_handler.setLevel(logging.INFO)
#app_log = logging.getLogger('yanzhe')
#app_log.setLevel(logging.INFO)
#app_log.addHandler(my_handler)

import logging

logging.basicConfig(level=logging.DEBUG, \
                    format="%(asctime)s" "[%(module)s:%(funcName)s:%(lineno)d]\n" "%(message)s \n" \
                   )
# filename='./log/loggmsg.log'
global Access_token
name = "postgres"
password = "1234"
port = "5432"
host = "127.0.0.1"
mrdate = '2000-01-01'
holdtime=3600
clicktime=10
db = PostgresqlDatabase('yyy', user=name, password=password, host=host, port=port)


class BaseModel(Model):
    class Meta:
        database = db


class workflow(BaseModel):
    userid = CharField()
    username = CharField()
    fatherid=IntegerField()
    state=CharField()
    flowname = CharField()
    flowdate = DateField()
    flowdetails = CharField()
    workflowtreename = CharField()
    updatetime = DateTimeField()
    writetime = DateTimeField()
    looker = CharField()
    remark = CharField()


class workflowtree(BaseModel):
    workflowid = IntegerField()
    userid = CharField()
    username = CharField()
    date = DateField()
    details = CharField()
    subworkflowid = IntegerField()
    writetime = DateTimeField()
    transmit = CharField()
    state=CharField()
    remark = CharField()


class userlist(BaseModel):
    userid = CharField()
    list = CharField()
    looker = CharField()
    remark = CharField()


class jobcontent(BaseModel):
    date = DateField()
    userid = CharField()
    content = CharField()
    writetime = DateTimeField()
    remark = CharField()


if (not workflow.table_exists()):
    workflow.create_table()
if (not userlist.table_exists()):
    userlist.create_table()
if (not jobcontent.table_exists()):
    jobcontent.create_table()

sToken = 'project'
sEncodingAESKey = 'PId9elWI4D1E1uVv4MCjzKdNBmPn9BWfnRqJoYuJz2X'
sCorpID = 'wx0af1900070a3ea37' #恩湃高科
sCorpSecret = 'nuoYdEnwZli9Oi016OjltxMIbYbyhtdyoC55uKtYkdP8a9ndVOFW4qNkvH_eydLz'

global Access_token
AccessTokenExpireDuration = 7200

web.config.debug = False

def RefreshAccessToken(threadName, delay):
    global Access_token
    url = 'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=' + sCorpID + '&corpsecret=' + sCorpSecret
    while True:
        resp = urllib2.urlopen(url)
        result = json.loads(resp.read())
        if ('access_token' in result.keys()):
            Access_token = result['access_token']
            logging.info("Refresh Access Token = |%r|" %Access_token)
            time.sleep(delay - 1)

# Create one thread to refresh access token as follows
try:
   thread.start_new_thread( RefreshAccessToken, ("Refresh-Access-Token-Thread", AccessTokenExpireDuration) )
except:
   logging.info( "Error: unable to start Refresh access token thread")


wxcpt = WXBizMsgCrypt(sToken, sEncodingAESKey, sCorpID)
render = web.template.render('templates')


def FindList(list, str2):
    bz = 0;
    for j in list:
        if (j == str2):
            bz = 1;
    return bz


def DelList(str1, str2):
    if (str1.strip() == ''):
        return ''
    list = str1.split(';')
    if (FindList(list, str2)):
        list.remove(str2)
    return ';'.join(list)


def AddList(str1, str2):
    if (str1.strip() == ''):
        return str2
    list = str1.split(';')
    if (FindList(list, str2)):
        str = str1
    else:
        list.append(str2)
        str = ';'.join(list)
    return str



def LoadWFTdetails(workflowid, userid, username,stateOC):

    dataline=[]
    sumline=[]
    datetitle=''
    xb=0
    workflowdata = workflow.get(workflow.id == workflowid)
    workflowtree._meta.db_table = workflowdata.workflowtreename
    for workflowtreedata in workflowtree().select().order_by(workflowtree.writetime.desc()):
        if (not workflowtreedata.state=='失效'):
            date=str(workflowtreedata.writetime.year)+'年'+str(workflowtreedata.writetime.month)+'月内容'
            date1=str(workflowtreedata.writetime.month)+'月'+str(workflowtreedata.writetime.day)+'日'+str(workflowtreedata.writetime).split(' ')[1]
            if (datetitle.strip()==''):
                datetitle=date
            if (not datetitle==date):
                if (xb==0):
                    fold='in'
                else:
                    fold=''
                sumline.append([dataline,datetitle,fold])
                dataline=[]
                datetitle=date
                xb=xb+1
            details=workflowtreedata.details
            if (workflowtreedata.state=='发起'):
                details='BEGIN：'+details
            if (workflowtreedata.userid == userid and workflowtreedata.subworkflowid==0 and stateOC=='open'):
                change = '<a class=\"btn btn-mini navbar-right\" href=\"#\" onclick=\"parent.location=\'/steppage?workflowtreeid=' + str(
                    workflowtreedata.id) + '&workflowid=' + str(workflowtreedata.workflowid) + '&date=' + str(
                    workflowtreedata.date) + '&details=' + workflowtreedata.details + '\'\"><small>>>修改</small></a>'
            else:
                change = ''
            if (workflowtreedata.subworkflowid!=0):
                user=userlist.get(userlist.userid == userid)
                list=user.list.split(';')
                workflowdata=workflow.get(workflow.id==workflowtreedata.subworkflowid)
               #if (FindList(list,str(workflowtreedata.subworkflowid)) and workflowdata.state!='关闭'):
                if (FindList(list,str(workflowtreedata.subworkflowid))):
                    details='<a onclick=\"parent.location=\'/workflowdetail?workflowid='+str(workflowtreedata.subworkflowid)+'\'\">'+'<i class=\"glyphicon glyphicon-list\"></i> 项目分支：'+workflowtreedata.details+'</a>'
                else:
                    details='<i class=\"glyphicon glyphicon-list\"></i> 项目分支：'+workflowtreedata.details
            line=[date1, details, workflowtreedata.username,change]
            dataline.append(line)
    if (xb==0):
        fold='in'
    else:
        fold=''
    sumline.append([dataline,datetitle,fold])
    return sumline

def LoadWFdetails(userid,stateOC):
    dataline=[]
    userlistdata = userlist.get(userlist.userid == userid)
    if (not userlistdata.list.strip() == ''):
        list = userlistdata.list.split(';')
        if (not userlistdata.looker.strip() == ''):
            looker = userlistdata.looker.split(';')
        else:
            looker = ''
        for workflowdata in workflow().select().where(workflow.id << list).order_by(workflow.updatetime.desc()):
            check=''
            if (not userlistdata.looker.strip() == ''):
                if (FindList(looker, str(workflowdata.id))):
                    check = 'checked'
            workflowtree._meta.db_table = workflowdata.workflowtreename
            participants=''
            for participant in workflowtree().select(workflowtree.username).distinct():
                participants+=participant.username+' '
            line=[workflowdata.id,workflowdata.flowname,workflowdata.updatetime,workflowdata.flowdate,workflowdata.flowdetails,workflowdata.id,check,participants]
            if (stateOC=='open' and workflowdata.state!='关闭'):
                dataline.append(line)
            if (stateOC=='close' and workflowdata.state=='关闭'):
                dataline.append(line)
    return dataline

def Post(url, data):
    req = urllib2.Request(url, data);
    response = urllib2.urlopen(req);

def Transmit(wft, sendee, time,userid):
    global Access_token
    if (not sendee.strip() == ''):
        bz=0
        if (wft.transmit.strip() == ''):
            wft.transmit = sendee
            bz=1
        else:
            list=wft.transmit.split(';')
            if (not FindList(list,sendee)):
                wft.transmit += ';' + sendee
                bz=1
        user = sendee.split('-')
        if (bz and user[0]!=userid):
            try:
                employeeList = userlist.get(userlist.userid == user[0])
                employeeList.list = AddList(employeeList.list, str(wft.workflowid))
                employeeList.looker = AddList(employeeList.looker, str(wft.workflowid))
                employeeList.save()
            except DoesNotExist:
                employeeList = userlist()
                employeeList.userid = user[0]
                employeeList.list = str(wft.workflowid)
                employeeList.looker = str(wft.workflowid)
                employeeList.remark = ''
                employeeList.save()

            wf = workflow.get(workflow.id == wft.workflowid)
            content = wft.username + '：项目《' + wf.flowname + '》组邀请您加入。'

            url = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=' + Access_token + '&debug=1'
            data = '{\"touser\":\"' + str(
                user[0]) + '\",\"msgtype\":\"text\",\"agentid\":\"0\",\"text\":{\"content\": \"' + str(
                content) + '\"},\"safe\":\"0\"}'
            Post(url, data)


def GetOption(workflowid,departments,userid):
    global Access_token
    options=''
    url='https://qyapi.weixin.qq.com/cgi-bin/department/list?access_token='+Access_token
    resp = urllib2.urlopen(url)
    result = json.loads(resp.read())
    for department in result['department']:
        if (FindList(departments,str(department['id']))):
            options+='<optgroup label=\"'+department['name']+'\"></optgroup>'
            url = 'https://qyapi.weixin.qq.com/cgi-bin/user/simplelist?access_token=' + Access_token + '&department_id='+str(department['id'])+'&fetch_child=1&status=0';
            resp = urllib2.urlopen(url)
            result = json.loads(resp.read())
            if (result['errcode'] == 0):
                for value in result['userlist']:
                    line='<option>' + value['userid'] + '-' + value['name'] + '</option>'
                    if (not workflowid==0):
                        employeeList = userlist.get(userlist.userid==value['userid'])
                        user=employeeList.get(userlist.userid==value['userid'])
                        list=user.list.split(';')
                        if (FindList(list,str(workflowid)) and userid!=value['userid']):
                            line='<option selected>' + value['userid'] + '-' + value['name'] + '</option>'
                    options += line
    return options


def WORKCONTENT(userid):
    s = ''
    for jobcontent1 in jobcontent().select().where(jobcontent.userid == userid):
        s += '<tr><th>' + str(jobcontent1.date) + '</th><th>' + jobcontent1.content + '</th></tr>'
    return s


def AddDepartment(userid,workflowid):
    global Access_token
    url = 'https://qyapi.weixin.qq.com/cgi-bin/user/get?access_token='+ Access_token + '&userid=' + userid
    resp = urllib2.urlopen(url)
    result = json.loads(resp.read())
    department = result['department']
    for departmentid in department:
        try:
            departmentList = userlist.get(userlist.userid == departmentid)
            departmentList.list=AddList(departmentList.list, workflowid)
            departmentList.save()
        except DoesNotExist:
            departmentList = userlist()
            departmentList.userid = departmentid
            departmentList.list =  workflowid
            departmentList.looker = ''
            departmentList.remark = ''
            departmentList.save()

urls = (
    '/', 'Index',
    '/sys', 'Syspage',
    '/checkworkflow', 'CheckWorkflow',
    '/addworkflowpage', 'AddWorkflow',
    '/addworkflow',  'AddWorkflow',
    '/workflowdetail', 'WorkflowDetail',
    '/steppage', 'Steppage',
    '/addsteppage', 'AddSteppage',
    '/changestep', 'AddSteppage',
    '/addstep', 'AddSteppage',
    '/weekworkpage', 'WeekWorkpage',
    '/addwork', 'WeekWorkpage',
    '/attontion', 'Attontion',
    '/help','Help',
    '/addsubworkflow','addsubworkflow',
    '/clostworkflow','clostworkflow')

class clostworkflow:
    def GET(self):
        cookies = web.cookies()
        logging.info("cookies data: |%r|" % cookies)
        if (cookies.get('userid') and cookies.get('stateOC')):
            userid=cookies.userid
            stateOC=cookies.stateOC
        else:
            return render.closepage()
        i=web.input()
        logging.info("web.input data: |%r|" % i)
        workflowdata=workflow.get(workflow.id==i.workflowid)
        workflowdata.state='关闭'
        workflowdata.save()
        return render.checkworkflow(LoadWFdetails(userid,stateOC))


class addsubworkflow:
    def GET(self):
        cookies = web.cookies()
        logging.info("cookies data: |%r|" % cookies)
        if (cookies.get('userid') and cookies.get('department')):
            userid=cookies.userid
            departments=cookies.department
        else:
            return render.closepage()
        i = web.input()
        logging.info("web.input data: |%r|" % i)
        return render.addworkflowpage(GetOption(0,departments,userid),i.workflowid)
class Help:
    def GET(self):
         return render.help()
class Attontion:
    def GET(self):
        cookies = web.cookies()
        logging.info("cookies data: |%r|" % cookies)
        if (cookies.get('userid')):
            userid=cookies.userid
        else:
            return render.closepage()
        i = web.input()
        logging.info("web.input data: |%r|" % i)
        if (i.attontion == 'true'):
            userlistdata = userlist.get(userlist.userid == userid)
            userlistdata.looker = AddList(userlistdata.looker, str(i.workflowid))
            userlistdata.save()
            workflowdata = workflow.get(workflow.id == i.workflowid)
            workflowdata.looker = AddList(workflowdata.looker, str(userid))
            workflowdata.save()
        else:
            userlistdata = userlist.get(userlist.userid == userid)
            userlistdata.looker = DelList(userlistdata.looker, str(i.workflowid))
            userlistdata.save()
            workflowdata = workflow.get(workflow.id == i.workflowid)
            workflowdata.looker = DelList(workflowdata.looker, str(userid))
            workflowdata.save()


class WeekWorkpage:
    def GET(self):
        cookies = web.cookies()
        logging.info("cookies data: |%r|" % cookies)
        if (cookies.get('userid') and cookies.get('username')):
            userid=cookies.userid
            username=cookies.username
        else:
            return render.closepage()
        return render.weekwork(userid, username, WORKCONTENT(userid))

    def POST(self):
        cookies = web.cookies()
        logging.info("cookies data: |%r|" % cookies)
        if (cookies.get('userid')):
            userid=cookies.userid
        else:
            return render.closepage()
        i = web.input(data=[])
        logging.info("web.input data: |%r|" % i)
        begin1 = i.data[2]
        begin2 = time.strptime(begin1, '%Y-%m-%d')
        begin = datetime.date(*begin2[:3])
        end1 = i.data[3]
        end2 = time.strptime(end1, '%Y-%m-%d')
        end = datetime.date(*end2[:3])
        for j in range((end - begin).days + 1):
            day = begin + datetime.timedelta(days=j)
            jobcontent1 = jobcontent()
            jobcontent1.date = day
            jobcontent1.userid = i.data[0]
            jobcontent1.content = i.data[4]
            jobcontent1.writetime = time.strftime('%Y-%m-%d %X', time.localtime(time.time()))
            jobcontent1.remark = ''
            jobcontent1.save()
        return render.weekwork(i.data[0], i.data[1], WORKCONTENT(i.data[0]))


#某一工作流具体步骤
class AddSteppage:
    def GET(self):
        i = web.input()
        logging.info("web.input data: |%r|" % i)
        return render.addsteppage(i.workflowid)

    def POST(self):
        cookies = web.cookies()
        logging.info("cookies data: |%r|" % cookies)
        if (cookies.get('userid') and cookies.get('username') and cookies.get('stateOC')):
            userid=cookies.userid
            username=cookies.username
            stateOC=cookies.stateOC
        else:
            return render.closepage()

        global Access_token
        i = web.input(data=[])
        logging.info("web.input data: |%r|" % i)
        nowtime = time.strftime('%Y-%m-%d %X', time.localtime(time.time()))
        workflowdata = workflow.get(workflow.id == i.data[3])

        workflowdata.updatetime = nowtime
        workflowdata.save()
        workflowtree._meta.db_table = workflowdata.workflowtreename
        bz=0
        if (i.data[0] == 'change'):
            workflowtreedataold = workflowtree.get(workflowtree.id == i.data[4])
            if (workflowtreedataold.state == '发起'):
                workflowdata.flowdetails = i.data[2]
                workflowdata.flowdate = i.data[1]
                workflowdata.save()
                bz=1
            workflowtreedataold.state='失效'
            workflowtreedataold.save()

        workflowtreedata = workflowtree()
        workflowtreedata.subworkflowid=0
        workflowtreedata.workflowid = i.data[3]
        workflowtreedata.userid = userid
        workflowtreedata.username = username
        workflowtreedata.remark = ''
        workflowtreedata.transmit = ''
        workflowtreedata.writetime = nowtime

        workflowtreedata.date = i.data[1]
        workflowtreedata.details = i.data[2]
        if (bz):
            workflowtreedata.state='发起'
        else:
            workflowtreedata.state=''
        k = web.input(option=[])
        addlist=k.option
        if (i.data[0]=='change'):
            if (workflowtreedataold.transmit.strip() == ''):
                oldlist=[]
            else:
                oldlist=workflowtreedataold.transmit.split(';')

            newlist=list(set(k.option))
            addlist=list(set(newlist).difference(set(oldlist)))
            dellist=list(set(oldlist).difference(set(newlist)))
            for sendee in dellist:
                if (sendee.strip()!=''):

                    workflowdata.looker = DelList(workflowdata.looker,sendee.split('-')[0])
                    user=userlist.get(userlist.userid==sendee.split('-')[0])
                    user.list=DelList(user.list,str(i.data[3]))
                    user.looker=DelList(user.looker,str(i.data[3]))
                    user.save()
        for sendee in addlist:
            if (sendee.strip()!=''):
                workflowdata.looker = AddList(workflowdata.looker, sendee.split('-')[0])
                Transmit(workflowtreedata,sendee, nowtime,userid)
                AddDepartment(sendee.split('-')[0],str(i.data[3]))
        workflowtreedata.save()

        if (not workflowdata.looker.strip() == ''):
            lists = workflowdata.looker.split(';')
            for everyone in lists:
                if (not userid == everyone):
                    content=username+'：项目《' +workflowdata.flowname + '》进展为「' + i.data[2] + '」'

                    url = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=' + Access_token + '&debug=1'
                    data = '{\"touser\":\"' + str(
                        everyone) + '\",\"msgtype\":\"text\",\"agentid\":\"0\",\"text\":{\"content\": \"' + str(
                        content) + '\"},\"safe\":\"0\"}'
                    Post(url, data)
        if (workflowdata.userid==userid):
            hidden='btn-danger'
        else:
            hidden='hidden'
        return render.workflowdetail(LoadWFTdetails(i.data[3], userid, username,stateOC),i.data[3], workflowdata.flowname,hidden,workflowdata.state)


class Steppage:
    def GET(self):
        cookies = web.cookies()
        logging.info("cookies data: |%r|" % cookies)
        if (cookies.get('userid') and cookies.get('department')):
            userid=cookies.userid
            departments=cookies.department
        else:
            return render.closepage()
        i = web.input()
        logging.info("web.input data: |%r|" % i)
        workflowdata=workflow.get(workflow.id==i.workflowid)
        workflowtree._meta.db_table = workflowdata.workflowtreename
        workflowtreedate=workflowtree.get(workflowtree.id==i.workflowtreeid)
        if (workflowtreedate.state=='发起'):
            choicepotion=''
        else:
            choicepotion='hidden=\"true\"'

        return render.steppage(GetOption(i.workflowid,departments,userid),choicepotion,i.workflowid, i.workflowtreeid, i.date, i.details)


#某一工作流详细内容
class WorkflowDetail:
    def GET(self):
        cookies = web.cookies()
        logging.info("cookies data: |%r|" % cookies)
        if (cookies.get('userid') and cookies.get('username') and cookies.get('stateOC')):
            userid=cookies.userid
            username=cookies.username
            stateOC=cookies.stateOC
        else:
            return render.closepage()
        i = web.input()
        logging.info("web.input data: |%r|" % i)
        workflowdata = workflow.get(workflow.id == i.workflowid)
        if (stateOC=='open'):
            if (workflowdata.userid==userid):
                hidden='btn-danger'
            else:
                hidden='hidden'
            return render.workflowdetail(LoadWFTdetails(i.workflowid, userid,username,stateOC),i.workflowid,workflowdata.flowname,hidden,workflowdata.state)
        else:
            return render.closeflowdetail(LoadWFTdetails(i.workflowid, userid,username,stateOC),workflowdata.flowname)

#项目汇总内容
class CheckWorkflow:
    def GET(self):
        cookies = web.cookies()
        logging.info("cookies data: |%r|" % cookies)
        if (cookies.get('userid') and cookies.get('stateOC')):
            userid=cookies.userid
            stateOC=cookies.stateOC
        else:
            return render.closepage()
        if (stateOC=='close'):
            return render.checkcloseflow(LoadWFdetails(userid,stateOC))
        else:
            return render.checkworkflow(LoadWFdetails(userid,stateOC))


class AddWorkflow:
    #增加工作流
    def POST(self):
        cookies = web.cookies()
        logging.info("cookies data: |%r|" % cookies)
        if (cookies.get('userid') and cookies.get('username') and cookies.get('stateOC')):
            userid=cookies.userid
            username=cookies.username
            stateOC=cookies.stateOC
        else:
            return render.closepage()

        i = web.input(data=[])
        logging.info("web.input data: |%r|" % i)
        workflowdata = workflow()
        nowtime = time.strftime('%Y-%m-%d %X', time.localtime(time.time()))
        nowtimetable = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
        workflowdata.userid = userid
        workflowdata.username = username
        workflowdata.state='打开'
        workflowdata.flowname = i.data[0]
        workflowdata.flowdate = i.data[1]
        workflowdata.flowdetails = i.data[2]
        workflowdata.updatetime = nowtime
        workflowdata.writetime = nowtime
        workflowdata.looker = AddList('', userid)
        workflowdata.remark = ''
        tablename = str(nowtimetable) + '_' + userid
        workflowdata.workflowtreename = tablename
        workflowdata.fatherid=i.data[3]
        workflowdata.save()

        workflowid = db.last_insert_id(db.get_cursor(), workflow)
        AddDepartment(userid,str(workflowid))
        userlistdata = userlist.get(userlist.userid == userid)
        userlistdata.list = AddList(userlistdata.list, str(workflowid))
        userlistdata.looker = AddList(userlistdata.looker, str(workflowid))
        userlistdata.save()

        workflowtree._meta.db_table = tablename
        if (not workflowtree.table_exists()):
            workflowtree.create_table()
        workflowtreedata = workflowtree()
        workflowtreedata.date = i.data[1]
        workflowtreedata.userid = userid
        workflowtreedata.username = username
        workflowtreedata.details = i.data[2]
        workflowtreedata.workflowid = workflowid
        workflowtreedata.writetime = nowtime
        workflowtreedata.subworkflowid=0
        workflowtreedata.remark = ''
        workflowtreedata.transmit = ''
        workflowtreedata.state='发起'
        workflowtreedata.save()

        if (i.data[3]!='0'):
            fatherworkflow=workflow.get(workflow.id == i.data[3])
            workflowtree._meta.db_table = fatherworkflow.workflowtreename
            detailsWFT=workflowtree()
            detailsWFT.date=i.data[1]
            detailsWFT.userid = userid
            detailsWFT.username = username
            detailsWFT.details = i.data[0]
            detailsWFT.workflowid =i.data[3]
            detailsWFT.transmit = ''
            detailsWFT.writetime = nowtime
            detailsWFT.remark = ''
            detailsWFT.subworkflowid=workflowid
            detailsWFT.state='子项目'
            detailsWFT.save()

        i = web.input(option=[])
        for option in i.option:
            workflowdata.looker = AddList(workflowdata.looker,option.split('-')[0])
            Transmit(workflowtreedata, option, nowtime,userid)
            AddDepartment(option.split('-')[0],str(workflowid))
        workflowdata.save()
        workflowtree._meta.db_table = tablename
        workflowtreedata.save()
        return render.checkworkflow(LoadWFdetails(userid,stateOC))

    #跳转至增加工作流页面
    def GET(self):
        cookies = web.cookies()
        logging.info("cookies data: |%r|" % cookies)
        if (cookies.get('userid') and cookies.get('department')):
            userid=cookies.userid
            departments=cookies.department
        else:
            return render.closepage()
        i = web.input()
        logging.info("web.input data: |%r|" % i)
        return render.addworkflowpage(GetOption(0,departments,userid),i.workflowid)

#首页内容
class Syspage:
    def GET(self):
        global Access_token

        #Wechat transfer the data to the server
        dataFromWeXin = web.input()
        logging.info("WeXin Send = |%s|" % dataFromWeXin)

        userid=''
        username=''
        position=''
        stateOC=''
        department=''
        if (dataFromWeXin.get('code')):
            code = dataFromWeXin.code
            stateOC=dataFromWeXin.state
            web.setcookie('stateOC', stateOC, holdtime)
            url = 'https://qyapi.weixin.qq.com/cgi-bin/user/getuserinfo?access_token=' \
                  + Access_token + '&code=' + code + '&agentid=0'

            logging.info("We Send URL= |%s|" % url)

            resp = urllib2.urlopen(url)
            result = json.loads(resp.read())

            logging.info('WeXin Response = |%s|' % result)
            if (result.has_key('UserId')):
                userid = result['UserId']
                url = 'https://qyapi.weixin.qq.com/cgi-bin/user/get?access_token=' \
                              + Access_token + '&userid=' + userid
                resp = urllib2.urlopen(url)
                result = json.loads(resp.read())

                logging.info("We send URL = |%s|" % url)
                logging.info("WeXin response = |%s|" % result)

                username = result['name']

                if (result.has_key('position')):
                    position=result['position']
                else:
                    position=''

                if (result.has_key('department')):
                    department=result['department']
                else:
                    department=''
                web.setcookie('userid',userid, holdtime)
                web.setcookie('username', username, holdtime)
                web.setcookie('position', position, holdtime)
                web.setcookie('department', department, holdtime)

        if (userid.strip()==''):
            cookies = web.cookies()
            if (cookies.get('userid')):
                userid=cookies.userid
                username=cookies.username
                position=cookies.position
                department=cookies.department
                stateOC=cookies.stateOC
            else:
                return render.closepage()

        url = 'https://qyapi.weixin.qq.com/cgi-bin/user/simplelist?access_token=' + Access_token + '&department_id=1&fetch_child=1&status=0';
        resp = urllib2.urlopen(url)
        result = json.loads(resp.read())
        for value in result['userlist']:
            try:
                employeeList = userlist.get(userlist.userid == value['userid'])
            except DoesNotExist:
                logging.info("add employeeList = |%s|" % userid)
                employeeList = userlist()
                employeeList.userid = value['userid']
                employeeList.list = ''
                employeeList.looker = ''
                employeeList.remark = ''
                employeeList.save()
        employeeList = userlist.get(userlist.userid == userid)
        logging.info("userID = |%s|,userName = |%s| ,position = |%s|,department = |%s|,stateOC = |%s|" % (userid,username,position,department,stateOC))
        if (position=='领导'):
            for departmentid in department:
                try:
                    departmentList = userlist.get(userlist.userid == str(departmentid))
                    if (not departmentList.list.strip()==''):
                        logging.info("department=|%s|,list=|%s|" % (departmentid,departmentList.list))
                        list = departmentList.list.split(';')
                        for id in list:
                            employeeList.list=AddList(employeeList.list,id)
                    logging.info("after add department's list,userID=|%s|,list=|%s|" % (userid,employeeList.list))
                    employeeList.save()
                except DoesNotExist:
                    departmentList = userlist()
                    departmentList.userid = departmentid
                    departmentList.list = ''
                    departmentList.looker = ''
                    departmentList.remark = ''
                    departmentList.save()
        if (stateOC=='close'):
            return render.checkcloseflow(LoadWFdetails(userid,stateOC))
        else:
            return render.checkworkflow(LoadWFdetails(userid,stateOC))

class Index:
    #验证接口用
    def GET(self):
        i = web.input()
        sVerifyMsgSig = i.msg_signature
        sVerifyTimeStamp = i.timestamp
        sVerifyNonce = i.nonce
        sVerifyEchoStr = i.echostr
        ret, sEchoStr = wxcpt.VerifyURL(sVerifyMsgSig, sVerifyTimeStamp, sVerifyNonce, sVerifyEchoStr)
        if (ret != 0):
            logging.info("ERR: VerifyURL ret: |%r|" % ret)
        logging.info(sEchoStr)
        return sEchoStr

    #平台互动
    def POST(self):
        dataFromWeXin = web.input()
        logging.info("WeXin send = |%r|" % dataFromWeXin)

        sReqData = web.data()
        sReqMsgSig = dataFromWeXin.msg_signature
        sReqTimeStamp = dataFromWeXin.timestamp
        sReqNonce = dataFromWeXin.nonce
        ret, sMsg = wxcpt.DecryptMsg(sReqData, sReqMsgSig, sReqTimeStamp, sReqNonce)
        logging.info("XML Message = |%s|" % sMsg)

        global Access_token
        xml = etree.fromstring(sMsg)
        msgType=xml.find("MsgType").text
        if (msgType=='text'):
            fromUser=xml.find("FromUserName").text
            title='欢迎使用项目管理系统'
            description='点击查看详细教程'
            url = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=' + Access_token + '&debug=1'
            data = '{\"touser\":\"' + fromUser + '\",\"msgtype\":\"news\",\"agentid\":\"0\",\"news\":{\"articles\" \
                    :[{\"title\":\"'+title+'\",\"description\":\"'+description+'\",\"url\":\"http://120.25.145.20:8080/help\",\"picurl\": \
                    \"http://120.25.145.20:8080/static/pic/help.jpg"}]}}'
            Post(url, data)
        if (msgType=='event'):
            event=xml.find("Event").text
            if (event=='subscribe'):
                fromUser=xml.find("FromUserName").text
                title='欢迎使用项目管理系统'
                description='点击查看详细教程'
                url = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=' + Access_token + '&debug=1'
                data = '{\"touser\":\"' + fromUser + '\",\"msgtype\":\"news\",\"agentid\":\"0\",\"news\":{\"articles\" \
                        :[{\"title\":\"'+title+'\",\"description\":\"'+description+'\",\"url\":\"http://120.25.145.20:8080/help\",\"picurl\": \
                        \"http://120.25.145.20:8080/static/pic/help.jpg"}]}}'
                Post(url, data)

        return ''


if __name__ == "__main__":
    app = web.application(urls, globals())
    app.run()
