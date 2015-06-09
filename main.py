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

# Thread
import thread

# DEBUG Options
import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s" \
                    "  [%(module)s:%(funcName)s:%(lineno)d]\n" \
                     "%(message)s \n")

global Access_token
name = "postgres"
password = "1234"
port = "5432"
host = "127.0.0.1"
mrdate = '2000-01-01'
holdtime=3600
db = PostgresqlDatabase('yyy', user=name, password=password, host=host, port=port)


class BaseModel(Model):
    class Meta:
        database = db


class workflow(BaseModel):
    userid = CharField()
    username = CharField()
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
    writetime = DateTimeField()
    transmit = CharField()
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
            logging.debug("Refresh Access Token = |%r|" %Access_token)
            time.sleep(delay - 1)

# Create one thread to refresh access token as follows
try:
   thread.start_new_thread( RefreshAccessToken, ("Refresh-Access-Token-Thread", AccessTokenExpireDuration) )
except:
   logging.debug( "Error: unable to start Refresh access token thread")


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



def LoadWFTdetails(workflowid, userid, username):
    s = ''
    data=[]
    workflowdata = workflow.get(workflow.id == workflowid)
    workflowtree._meta.db_table = workflowdata.workflowtreename
    for workflowtreedata in workflowtree().select().order_by(workflowtree.date.desc()):
        s += '<div class=\"panel-heading icon\"><i class=\"glyphicon glyphicon-time\"></i></div>'
        if (workflowtreedata.userid == userid):
            change = '<a class=\"btn btn-mini\" href=\"#\" onclick=\"parent.location=\'/steppage?workflowtreeid=' + str(
                workflowtreedata.id) + '&workflowid=' + str(workflowtreedata.workflowid) + '&date=' + str(
                workflowtreedata.date) + '&details=' + workflowtreedata.details + '\'\"><code>>>修改</code></a>'
        else:
            change = ''
        line=[workflowtreedata.date, workflowtreedata.details, workflowtreedata.username,change]
        data.append(line)
    return data

def LoadWFdetails(userid):
    data=[]
    userlistdata = userlist.get(userlist.userid == userid)
    if (not userlistdata.list.strip() == ''):
        list = userlistdata.list.split(';')
        if (not userlistdata.looker.strip() == ''):
            looker = userlistdata.looker.split(';')
        else:
            looker = ''
        for workflowdata in workflow().select().where(workflow.id << list).order_by(workflow.updatetime.desc()):
            check = ''
            if (not userlistdata.looker.strip() == ''):
                if (FindList(looker, str(workflowdata.id))):
                    check = 'checked'
            workflowtree._meta.db_table = workflowdata.workflowtreename
            participants=''
            for participant in workflowtree().select(workflowtree.username).distinct():
                participants+=participant.username+' '
            line=[workflowdata.id,workflowdata.flowname,workflowdata.updatetime,workflowdata.flowdate,workflowdata.flowdetails,workflowdata.id,check,participants]
            data.append(line)
    return data

def Post(url, data):
    req = urllib2.Request(url, data);
    response = urllib2.urlopen(req);


def Transmit(wft, sendee, time):
    global Access_token
    if (not sendee.strip() == ''):
        if (wft.transmit.strip() == ''):
            wft.transmit = '转发至:' + sendee
        else:
            wft.transmit += ';' + sendee
        user = sendee.split('-')
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
        content = wft.username + '：项目《' + wf.flowname + '》进展为「' + wft.details + '」'+'，并邀请您加入。'

        url = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=' + Access_token + '&debug=1'
        data = '{\"touser\":\"' + str(
            user[0]) + '\",\"msgtype\":\"text\",\"agentid\":\"0\",\"text\":{\"content\": \"' + str(
            content) + '\"},\"safe\":\"0\"}'
        Post(url, data)


def GetOption():
    global Access_token

    #options = '<option></option>'
    #<optgroup label="Eastern Time Zone">
    #</optgroup>
    options=''
    url='https://qyapi.weixin.qq.com/cgi-bin/department/list?access_token='+Access_token
    resp = urllib2.urlopen(url)
    result = json.loads(resp.read())
    for department in result['department']:
        if (department['parentid']==1):
            options+='<optgroup label=\"'+department['name']+'\"></optgroup>'
            url = 'https://qyapi.weixin.qq.com/cgi-bin/user/simplelist?access_token=' + Access_token + '&department_id='+str(department['id'])+'&fetch_child=1&status=0';
            resp = urllib2.urlopen(url)
            result = json.loads(resp.read())
            if (result['errcode'] == 0):
                for value in result['userlist']:
                    options += '<option>' + value['userid'] + '-' + value['name'] + '</option>'
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
    '/attontion', 'Attontion')


class Attontion:
    def GET(self):
        cookies = web.cookies()
        if (cookies.get('userid')):
            userid=cookies.userid
        else:
            return render.closepage()
        i = web.input()
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
        if (cookies.get('userid')):
            userid=cookies.userid
            username=cookies.username
        else:
            return render.closepage()
        return render.weekwork(userid, username, WORKCONTENT(userid))

    def POST(self):
        i = web.input(data=[])
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
        cookies = web.cookies()
        if (cookies.get('userid')):
            userid=cookies.userid
            username=cookies.username
        else:
            return render.closepage()
        i = web.input()
        return render.addsteppage(GetOption(), i.workflowid)

    def POST(self):
        cookies = web.cookies()
        if (cookies.get('userid')):
            userid=cookies.userid
            username=cookies.username
        else:
            return render.closepage()
        global Access_token
        i = web.input(data=[])

        nowtime = time.strftime('%Y-%m-%d %X', time.localtime(time.time()))
        workflowdata = workflow.get(workflow.id == i.data[3])
        workflowdata.updatetime = nowtime
        workflowdata.save()
        workflowtree._meta.db_table = workflowdata.workflowtreename
        if (i.data[0] == 'change'):
            workflowtreedata = workflowtree.get(workflowtree.id == i.data[4])
            if (workflowtreedata.id == 1):
                workflowdata.flowdetails = i.data[2]
                workflowdata.flowdate = i.data[1]
                workflowdata.save()
            workflowtreedata.date = i.data[1]
            workflowtreedata.details = i.data[2]
            workflowtreedata.save()
        else:
            workflowtreedata = workflowtree()
            workflowtreedata.workflowid = i.data[3]
            workflowtreedata.userid = userid
            workflowtreedata.username = username
            workflowtreedata.remark = ''
            workflowtreedata.transmit = ''
            workflowtreedata.writetime = nowtime
            k = web.input(option=[])
            workflowtreedata.date = i.data[1]
            workflowtreedata.details = i.data[2]
            for sendee in k.option:
                workflowdata.looker = AddList(workflowdata.looker, sendee.split('-')[0])
                Transmit(workflowtreedata,sendee, nowtime)
            workflowtreedata.save()

        if (not workflowdata.looker.split() == ''):
            lists = workflowdata.looker.split(';')
            for list in lists:
                if (not userid == list):
                    content=username+'：项目《' +workflowdata.flowname + '》进展为「' + i.data[2] + '」'

                    url = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=' + Access_token + '&debug=1'
                    data = '{\"touser\":\"' + str(
                        list) + '\",\"msgtype\":\"text\",\"agentid\":\"0\",\"text\":{\"content\": \"' + str(
                        content) + '\"},\"safe\":\"0\"}'
                    Post(url, data)

        return render.workflowdetail(LoadWFTdetails(workflowtreedata.workflowid, userid, username),i.data[3], workflowdata.flowname)


class Steppage:
    def GET(self):
        cookies = web.cookies()
        if (cookies.get('userid')):
            userid=cookies.userid
            username=cookies.username
        else:
            return render.closepage()
        i = web.input()
        return render.steppage(i.workflowid, i.workflowtreeid, i.date, i.details)


#某一工作流详细内容
class WorkflowDetail:
    def GET(self):
        cookies = web.cookies()
        if (cookies.get('userid')):
            userid=cookies.userid
            username=cookies.username
        else:
            return render.closepage()
        i = web.input()
        print i
        print cookies
        print '--------------'
        workflowdata = workflow.get(workflow.id == i.workflowid)
        return render.workflowdetail(LoadWFTdetails(i.workflowid, userid,username),i.workflowid,workflowdata.flowname)

#项目汇总内容
class CheckWorkflow:
    def GET(self):
        cookies = web.cookies()
        if (cookies.get('userid')):
            userid=cookies.userid
            username=cookies.username
        else:
            return render.closepage()
        return render.checkworkflow(LoadWFdetails(userid))


class AddWorkflow:
    #增加工作流
    def POST(self):
        cookies = web.cookies()
        if (cookies.get('userid')):
            userid=cookies.userid
            username=cookies.username
        else:
            return render.closepage()
        i = web.input(data=[])
        workflowdata = workflow()
        nowtime = time.strftime('%Y-%m-%d %X', time.localtime(time.time()))
        workflowdata.userid = userid
        workflowdata.username = username
        workflowdata.flowname = i.data[0]
        workflowdata.flowdate = i.data[1]
        workflowdata.flowdetails = i.data[2]
        workflowdata.updatetime = nowtime
        workflowdata.writetime = nowtime
        workflowdata.looker = AddList('', userid)
        workflowdata.remark = ''
        tablename = str(nowtime) + userid
        workflowdata.workflowtreename = tablename
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
        workflowtreedata.transmit = ''
        workflowtreedata.writetime = nowtime
        workflowtreedata.remark = ''
        workflowtreedata.save()
        i = web.input(option=[])
        for option in i.option:
            Transmit(workflowtreedata, option, nowtime)
            workflowdata.looker = AddList(workflowdata.looker,option.split('-')[0])
            AddDepartment(option.split('-')[0],str(workflowid))
        workflowdata.save()
        return render.checkworkflow(LoadWFdetails(userid))

    #跳转至增加工作流页面
    def GET(self):
        cookies = web.cookies()

        if (cookies.get('userid')):
            userid=cookies.userid
            username=cookies.username
        else:
            return render.closepage()
        return render.addworkflowpage(GetOption())

#首页内容
class Syspage:
    def GET(self):
        global Access_token

        #Wechat transfer the data to the server
        dataFromWeXin = web.input()

        logging.debug("WeXin Send = |%s|" % dataFromWeXin)

        userid=''
        username=''
        position=''
        department=''
        if (dataFromWeXin.get('code')):
            code = dataFromWeXin.code
            url = 'https://qyapi.weixin.qq.com/cgi-bin/user/getuserinfo?access_token=' \
                  + Access_token + '&code=' + code + '&agentid=0'

            logging.debug("We Send URL= |%s|" % url)

            resp = urllib2.urlopen(url)
            result = json.loads(resp.read())

            logging.debug('WeXin Response = |%s|' % result)
            if (result.has_key('UserId')):
                userid = result['UserId']
                url = 'https://qyapi.weixin.qq.com/cgi-bin/user/get?access_token=' \
                              + Access_token + '&userid=' + userid
                resp = urllib2.urlopen(url)
                result = json.loads(resp.read())

                logging.debug("We send URL = |%s|" % url)
                logging.debug("WeXin response = |%s|" % result)

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
            else:
                return render.closepage()
        try:
            employeeList = userlist.get(userlist.userid == userid)
            logging.debug("employeeList = |%r|" % employeeList)

        except DoesNotExist:
            employeeList = userlist()
            employeeList.userid = userid
            employeeList.list = ''
            employeeList.looker = ''
            employeeList.remark = ''
            employeeList.save()

        logging.debug("userID = |%s|, userName = |%s|" % (userid, username))

        if (position=='领导'):
            for departmentid in department:
                try:
                    departmentList = userlist.get(userlist.userid == str(departmentid))
                    if (not departmentList.list.strip()==''):
                        list = departmentList.list.split(';')
                        for id in list:
                            employeeList.list=AddList(employeeList.list,id)
                    employeeList.save()
                except DoesNotExist:
                    departmentList = userlist()
                    departmentList.userid = departmentid
                    departmentList.list = ''
                    departmentList.looker = ''
                    departmentList.remark = ''
                    departmentList.save()
        return render.checkworkflow(LoadWFdetails(userid))

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
            print "ERR: VerifyURL ret: " + str(ret)
        print sEchoStr
        return sEchoStr

    #平台互动
    def POST(self):
        dataFromWeXin = web.input()
        logging.debug("WeXin send = |%r|" % dataFromWeXin)

        sReqData = web.data()
        sReqMsgSig = dataFromWeXin.msg_signature
        sReqTimeStamp = dataFromWeXin.timestamp
        sReqNonce = dataFromWeXin.nonce
        ret, sMsg = wxcpt.DecryptMsg(sReqData, sReqMsgSig, sReqTimeStamp, sReqNonce)
        logging.debug("XML Message = |%s|" % sMsg)

        return ''

if __name__ == "__main__":
    app = web.application(urls, globals())
    app.run()
