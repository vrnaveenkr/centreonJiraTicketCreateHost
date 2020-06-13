import requests
import json
import sys


#Variable Declaration



def getToken(username,password,url):
    payload = "{\r\n  \"security\": {\r\n    \"credentials\": {\r\n      \"login\": \""+username+"\",\r\n      \"password\": \""+password+"\"\r\n    }\r\n  }\r\n}"
    headers = {
    'Content-Type': 'application/json'
    }
    authURL = url + 'login'
    authTokenResponse = requests.request("POST", authURL, headers=headers, data = payload)
    authTokenJson = json.loads(authTokenResponse.text)
    return (authTokenJson['security']['token'])


#Getting Parent Host Details of the object
def getParentHostname(connURL,Token,hostname):
    url = connURL+"action=action&object=centreon_clapi"
    payload = "{\r\n  \"action\": \"getparent\",\r\n  \"object\": \"host\",\r\n  \"values\": \""+hostname+"\"\r\n}"
    headers = {
    'centreon-auth-token': Token,
    'Content-Type': 'application/json'
    }
    pHostNameResponse = requests.request("POST", url, headers=headers, data = payload)
    parentHostnameJson =  json.loads(pHostNameResponse.text)
    for item in parentHostnameJson['result']:
        return(item['name'])



#Get the parent host status
def getHostState(connURL,Token,Hostname):
    url = connURL+"object=centreon_realtime_hosts&action=list&fields=id,name,alias,address,state,state_type,output,next_check,acknowledged,instance&search="+Hostname
    payload = {}
    headers = {
    'Content-Type': 'application/json',
    'centreon-auth-token': Token
    }
    HostStateresponse = requests.request("GET", url, headers=headers, data = payload)
    HostStateresponseJson = json.loads(HostStateresponse.text)

    PStateRepo = {} #This repo will hold the all the status of parent host
    
    for item in HostStateresponseJson:
        PStateRepo['id'] = item['id']
        PStateRepo['name'] = item['name']
        PStateRepo['state'] = item['state']
        PStateRepo['address'] = item['address']
        PStateRepo['output'] = item['output']
        PStateRepo['acknowledged'] = item['acknowledged']
        PStateRepo['instance_name'] = item['instance_name']
    return PStateRepo


#Set Acknowledgement to Host using APIV2
def setAckHost(connURL,Token,hostid,JiraResponse):
    url = connURL + "monitoring/hosts/"+hostid+"/acknowledgements"
    payload = "{\r\n  \"comment\": \""+JiraResponse+"\",\r\n  \"is_notify_contacts\": false,\r\n  \"is_persistent_comment\": true,\r\n  \"is_sticky\": true,\r\n  \"with_services\": true\r\n}"
    headers = {
    'X-AUTH-TOKEN': Token,
    'Content-Type': 'text/plain'
    }
    Ackresponse = requests.request("POST", url, headers=headers, data = payload)


#Get Poller Details
def getPollerStatus(connURL,Token):
    url = connURL + "action=action&object=centreon_clapi"
    payload = "{\r\n    \"action\": \"show\",\r\n    \"object\": \"INSTANCE\"\r\n}"
    headers = {
    'centreon-auth-token': Token,
    'Content-Type': 'application/json'
    }
    getPollerResponse = requests.request("POST", url, headers=headers, data = payload)
    getPollerJson = json.loads(getPollerResponse.text)

    pollerRepo = {}#This will hold all poller Details

    for item in getPollerJson['result']:
        pollerRepo['id'] = item ['id']
        pollerRepo['name'] = item ['name']
        pollerRepo['ip address'] = item ['ip address']
        pollerRepo['activate'] = item ['activate']
        pollerRepo['status'] = item ['status']
    return pollerRepo



#Jira Ticket Creation
def jiraTicketCreate(jiraURL,id,desc,summary):

    url = jiraURL

    payload = "{\r\n    \"fields\": {\r\n       \"project\":\r\n       {\r\n          \"id\": \""+id+"\"\r\n       },\r\n       \"summary\":\""+summary+"\",\r\n       \"description\":\""+desc+"\",\r\n       \"issuetype\": {\r\n          \"id\": \""+id+"\"\r\n       }\r\n   }\r\n}"
    headers = {
    'Authorization': 'Basic dnJuYXZlZW5rcjpXZWxjb21lQDE=',
    'Content-Type': 'application/json'
    }

    jiraResponse = requests.request("POST", url, headers=headers, data = payload)
    jiraResponseJson = json.loads(jiraResponse.text)
    return jiraResponseJson



#Ticket Creation Test Criteria
def testLogic(getHostDetails,getPHostDetails,PollerInfo,jiraURL,centURLV2,sessionToken):

    if (PollerInfo['activate'] == '1') and (PollerInfo['status'] == '1'):

        if(getPHostDetails == 'NA'):
            details = getHostDetails['name']+' '+getHostDetails['output']
            details = details.replace('\n', ' ').replace('\r', '')
            jira = jiraTicketCreate(jiraURL,'10000',details,details)
            jiraCentUpdate = jira['key']+', '+ jira['self']
            setAckHost(centURLV2,sessionToken,getHostDetails['id'],jiraCentUpdate)

        elif (getPHostDetails['state'] != '0') and (getPHostDetails['acknowledged'] == '0'):
            #Call Jira Ticket script
            print("Jira Ticket created for Phost")
            details = getPHostDetails['name']+' '+getPHostDetails['output']
            details = details.replace('\n', ' ').replace('\r', '')
            jira = jiraTicketCreate(jiraURL,'10000',details,details)
            jiraCentUpdate = jira['key']+', '+ jira['self']
            setAckHost(centURLV2,sessionToken,getPHostDetails['id'],jiraCentUpdate)

        elif (getPHostDetails['state'] != '0') and (getPHostDetails['acknowledged'] == '1'):
            print("Phost issue already ack")
            pass

        elif (getPHostDetails['state'] == '0') and (getHostDetails['acknowledged'] == '0'):
            details = getHostDetails['name']+' '+getHostDetails['output']
            details = details.replace('\n', ' ').replace('\r', '')
            jira = jiraTicketCreate(jiraURL,'10000',details,details)
            jiraCentUpdate = jira['key']+', '+ jira['self']
            setAckHost(centURLV2,sessionToken,getHostDetails['id'],jiraCentUpdate)
            print("Host issue  acknowledged")
            

        elif (getPHostDetails['state'] == '0') and (getHostDetails['acknowledged'] == '1'):
            print("Host issue already acknowledged")
            pass

    else:
        pass

#Main Logic combaining all function
def centJiraCore(hostname):

    centURLV2 = "http://10.10.100.106/centreon/api/latest/"
    centURLV1 = "http://10.10.100.106/centreon/api/index.php?"
    jiraURL = "http://10.10.100.106:8086/rest/api/2/issue/"
    hostname = hostname

    #Auth Token Holder                
    sessionToken = getToken('admin','Welcome@1',centURLV2)
    #Affected Host all Details Holder
    getHostDetails = getHostState(centURLV1,sessionToken,hostname)
    #Parent Hostname Holder
    parentHostName = getParentHostname(centURLV1,sessionToken,hostname)
    #Parent Host all Details Holder
    if (parentHostName != None):
        getPHostDetails = getHostState(centURLV1,sessionToken,parentHostName)
        print(getPHostDetails)
    else:
        getPHostDetails = 'NA'
    #Poller Status Holder
    PollerStatus = getPollerStatus(centURLV1,sessionToken)
    #TestLogic
    jc = testLogic(getHostDetails,getPHostDetails,PollerStatus,jiraURL,centURLV2,sessionToken)


if __name__ == "__main__":
    hostname = sys.argv[1]
    centJiraCore(hostname)
    


