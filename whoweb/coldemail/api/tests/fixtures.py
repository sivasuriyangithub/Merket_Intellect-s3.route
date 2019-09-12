# https://www.softwarelogin.com/api.php?&area=email&action=getcampaigns&output=json&limit=10
campaigns = """
{
    "records": "1786",
    "campaign": [
        {
            "id": "2070690",
            "title": "WKVIP_Chairman Mom - Square Employees - Letter 1",
            "status": "Completed",
            "scheduledate": "July 23, 2019, 03:06:00 pm",
            "starttime": "July 23, 2019, 03:13:51 pm",
            "endtime": "July 23, 2019, 03:47:01 pm",
            "lastupdate": {},
            "sent": "426",
            "views": "0",
            "clicks": "0",
            "optouts": "0",
            "conversions": "0"
        },
        {
            "id": "2070672",
            "title": "WKVIP_Chairman Mom - Employees6 Letter 2",
            "status": "Completed",
            "scheduledate": "July 23, 2019, 01:01:00 pm",
            "starttime": "July 23, 2019, 03:06:49 pm",
            "endtime": "July 23, 2019, 03:43:15 pm",
            "lastupdate": {},
            "sent": "23062",
            "views": "459",
            "clicks": "849",
            "optouts": "396",
            "conversions": "0"
        },
        {
            "id": "2070671",
            "title": "WKVIP_X2AI_Employee ALL Del i75 - 125k -  no tracking - Letter 1",
            "status": "Sending",
            "scheduledate": "July 23, 2019, 12:58:00 pm",
            "starttime": "July 23, 2019, 01:01:03 pm",
            "endtime": {},
            "lastupdate": {},
            "sent": "16000",
            "views": "566",
            "clicks": "0",
            "optouts": "27",
            "conversions": "0"
        },
        {
            "id": "2070564",
            "title": "WK_VIP_Bricleir_Innovation_Execs_20190709 - m3 ^ip ER 161949",
            "status": "Completed",
            "scheduledate": "July 23, 2019, 01:07:39 am",
            "starttime": "July 23, 2019, 06:00:53 am",
            "endtime": "July 23, 2019, 07:49:16 am",
            "lastupdate": {},
            "sent": "2667",
            "views": "32",
            "clicks": "35",
            "optouts": "0",
            "conversions": "0"
        },
        {
            "id": "2070546",
            "title": "WKVIP_JisekiHealth_SMBs_20190717 - m2 ^ip ER 161949",
            "status": "Sending",
            "scheduledate": "July 22, 2019, 04:33:08 pm",
            "starttime": "July 22, 2019, 06:01:54 pm",
            "endtime": {},
            "lastupdate": {},
            "sent": "25500",
            "views": "460",
            "clicks": "295",
            "optouts": "21",
            "conversions": "0"
        },
        {
            "id": "2070437",
            "title": "WK_VIP_CitizensCapital_20190717 - m2 ^ip ER 161949",
            "status": "Completed",
            "scheduledate": "July 22, 2019, 02:51:58 am",
            "starttime": "July 22, 2019, 06:01:58 am",
            "endtime": "July 22, 2019, 10:45:06 pm",
            "lastupdate": {},
            "sent": "14680",
            "views": "591",
            "clicks": "545",
            "optouts": "2",
            "conversions": "0"
        }
    ]
}
"""

# https://www.softwarelogin.com/api.php?&area=email&action=createcampaign&output=json&title=test&listid=407770&messageid=171431&profileid=160382&whoisid=8200&subject=test&fromname=test&fromaddress=dev@whoknows.com
create_campaign = """
{
    "success": "Campaign Added to Queue",
    "id": "2070703"
}
"""
# https://www.softwarelogin.com/api.php?&area=email&action=getcampaigns&output=json&id=2070672
campaign = """
{
    "records": "1",
    "campaign": {
        "id": "2070703",
        "title": "WKVIP_Chairman Mom - Employees6 Letter 2",
        "status": "Completed",
        "scheduledate": "July 23, 2019, 01:01:00 pm",
        "starttime": "July 23, 2019, 03:06:49 pm",
        "endtime": "July 23, 2019, 03:43:15 pm",
        "lastupdate": {},
        "sent": "23062",
        "views": "459",
        "clicks": "849",
        "optouts": "396",
        "conversions": "0"
    }
}
"""
# https://www.softwarelogin.com/api.php?&area=email&action=getcampaigndetail&output=json&id=2070672
campaign_detail = """
{
    "campaign": {
        "id": "2070703",
        "title": "WKVIP_Chairman Mom - Employees6 Letter 2",
        "status": "Completed",
        "scheduledate": "July 23, 2019, 01:01:00 pm",
        "starttime": "July 23, 2019, 03:06:49 pm",
        "endtime": "July 23, 2019, 03:43:15 pm",
        "lastupdate": "July 23, 2019, 03:43:13 pm",
        "sent": "23062",
        "views": "459",
        "clicks": "849",
        "optouts": "396",
        "conversions": "0",
        "fblreports": "0",
        "listid": "431142",
        "subject": "You are invited to join Chairman Mom",
        "messageid": "181798",
        "adklistid": "0",
        "adksubid": {},
        "suppression": {
            "listid": [
                "423544",
                "406761"
            ]
        },
        "profileid": "161949",
        "serverid": "2116",
        "domain": "getwhoknowsrecruit.net",
        "ips": {
            "ip": "205.236.251.127"
        },
        "fromname": "Vanity Holt",
        "fromaddress": "vanityholtchairmanmom",
        "sendto": "Full",
        "startindex": "0",
        "endindex": "23073",
        "dkim": "Yes",
        "usedeliverygroups": "Yes",
        "isabtest": "No",
        "socialshares": "0",
        "randomizelist": "0",
        "speed": "5000 Emails Per hour",
        "good": "161",
        "blocked": "200",
        "timedout": "146",
        "unknown": "0",
        "addressfail": "0",
        "domainfail": "0",
        "retryqueue": "22555",
        "reporturl": "https://www.softwarelogin.com/report.php?id=2070672&r=d819f7dc30c3427792aea85985e1933060825ef4"
    }
}
"""
# https://www.softwarelogin.com/api.php?&area=email&action=getclicklog&output=json&limit=10&id=2070672
campaign_clicklog = campaign_openlog = """
{
    "records": "850",
    "uniquerecords": "4",
    "log": [
        {
            "email": "myriam.mogollon@orlandohealth.com",
            "datecreated": "July 23, 2019, 04:59:57 pm",
            "link": "https://&lt;#url#&gt;",
            "ip": "12.167.151.116",
            "country": "US",
            "useragent": "Windows XP Internet Explorer 8.0"
        },
        {
            "email": "mitzi.moore@orlandohealth.com",
            "datecreated": "July 23, 2019, 04:46:36 pm",
            "link": "https://&lt;#url#&gt;",
            "ip": "12.167.151.115",
            "country": "US",
            "useragent": "Windows XP Internet Explorer 8.0"
        },
        {
            "email": "myriam.mogollon@orlandohealth.com",
            "datecreated": "July 23, 2019, 04:38:31 pm",
            "link": "https://&lt;#url#&gt;",
            "ip": "12.167.151.116",
            "country": "US",
            "useragent": "Windows XP Internet Explorer 8.0"
        },
        {
            "email": "ingrit.martinez@orlandohealth.com",
            "datecreated": "July 23, 2019, 04:20:24 pm",
            "link": "https://&lt;#url#&gt;",
            "ip": "52.59.102.42",
            "country": "US",
            "useragent": "Mac OS X 10.13.2 Google Chrome 63.0.3239.84"
        },
        {
            "email": "shanay.cogdell@orlandohealth.com",
            "datecreated": "July 23, 2019, 04:20:13 pm",
            "link": "https://&lt;#url#&gt;",
            "ip": "52.59.102.42",
            "country": "US",
            "useragent": "Mac OS X 10.13.2 Google Chrome 63.0.3239.84"
        },
        {
            "email": "myriam.mogollon@orlandohealth.com",
            "datecreated": "July 23, 2019, 04:16:50 pm",
            "link": "https://&lt;#url#&gt;",
            "ip": "65.154.226.126",
            "country": "US",
            "useragent": "Windows 7 Google Chrome 73.0.3683.75"
        },
        {
            "email": "myriam.mogollon@orlandohealth.com",
            "datecreated": "July 23, 2019, 04:16:45 pm",
            "link": "https://&lt;#url#&gt;",
            "ip": "65.154.226.126",
            "country": "US",
            "useragent": "Windows 7 Google Chrome 73.0.3683.75"
        },
        {
            "email": "ingrit.martinez@orlandohealth.com",
            "datecreated": "July 23, 2019, 04:15:48 pm",
            "link": "https://&lt;#url#&gt;",
            "ip": "12.167.151.117",
            "country": "US",
            "useragent": "Windows XP Internet Explorer 8.0"
        },
        {
            "email": "myriam.mogollon@orlandohealth.com",
            "datecreated": "July 23, 2019, 04:12:49 pm",
            "link": "https://&lt;#url#&gt;",
            "ip": "194.99.104.30",
            "country": "DE",
            "useragent": "GNU/Linux x64 IceWeasel 17.0.1"
        },
        {
            "email": "myriam.mogollon@orlandohealth.com",
            "datecreated": "July 23, 2019, 04:12:49 pm",
            "link": "https://&lt;#url#&gt;",
            "ip": "194.99.104.30",
            "country": "DE",
            "useragent": "GNU/Linux x64 IceWeasel 17.0.1"
        }
    ]
}
"""
campaign_clicklog_empty = campaign_openlog_empty = """
{
    "records": "0",
    "uniquerecords": "0"
}
"""
campaign_clicklog_single = """
{
    "records": "1",
    "uniquerecords": "1",
    "log": {
            "email": "myriam.mogollon@orlandohealth.com",
            "datecreated": "July 23, 2019, 04:12:49 pm",
            "link": "https://&lt;#url#&gt;",
            "ip": "194.99.104.30",
            "country": "DE",
            "useragent": "GNU/Linux x64 IceWeasel 17.0.1"
        }
}
"""
create_coldlist = """
{
    "success": "List Created",
    "id": "431142"
}
"""

# https://www.softwarelogin.com/api.php?&area=email&action=uploadlistbyurl&output=json&title="test"&url=dev.whoknows.com/404.txt
create_coldlist_by_url = """
{
    "importid": "29294",
    "listid": "431168",
    "status": "Processing"
}
"""
# https://www.softwarelogin.com/api.php?&area=email&action=getlists&output=json&id=431142
coldlist = """
{
    "records": "1",
    "list": {
        "id": "431142",
        "title": "Chairman Mom Employees 20190723",
        "status": {},
        "total": "23073",
        "active": "23023",
        "datecreated": "July 23, 2019, 12:57:20 pm",
        "isfolder": "0",
        "optinlist": "0",
        "suppressionlist": "0",
        "suppressionmd5": "0",
        "leased": "0",
        "locked": "0",
        "filesize": "0",
        "liststatsurl": "https://www.softwarelogin.com/liststats.php?id=431142&r=53360284def5fd89700ce2a4bb620ac485d6e0b7"
    }
}
"""
# https://www.softwarelogin.com/api.php?&area=email&action=getlists&output=json&limit=5
coldlists = """
{
    "records": "2257",
    "list": [
        {
            "id": "424287",
            "title": "WKVIP",
            "status": {},
            "total": {},
            "active": {},
            "datecreated": "March 22, 2019, 05:41:27 pm",
            "isfolder": "1",
            "optinlist": "0",
            "suppressionlist": "0",
            "suppressionmd5": "0",
            "leased": "0",
            "locked": "0",
            "filesize": "0",
            "liststatsurl": {}
        },
        {
            "id": "412902",
            "title": "User Lists",
            "status": {},
            "total": {},
            "active": {},
            "datecreated": "September 25, 2018, 11:36:08 am",
            "isfolder": "1",
            "optinlist": "0",
            "suppressionlist": "0",
            "suppressionmd5": "0",
            "leased": "0",
            "locked": "0",
            "filesize": "0",
            "liststatsurl": {}
        },
        {
            "id": "406876",
            "title": "OMFM",
            "status": {},
            "total": {},
            "active": {},
            "datecreated": "June 15, 2018, 02:17:17 pm",
            "isfolder": "1",
            "optinlist": "0",
            "suppressionlist": "0",
            "suppressionmd5": "0",
            "leased": "0",
            "locked": "0",
            "filesize": "0",
            "liststatsurl": {}
        },
        {
            "id": "431142",
            "title": "Chairman Mom Employees 20190723",
            "status": {},
            "total": "23073",
            "active": "23023",
            "datecreated": "July 23, 2019, 12:57:20 pm",
            "isfolder": "0",
            "optinlist": "0",
            "suppressionlist": "0",
            "suppressionmd5": "0",
            "leased": "0",
            "locked": "0",
            "filesize": "0",
            "liststatsurl": "https://www.softwarelogin.com/liststats.php?id=431142&r=53360284def5fd89700ce2a4bb620ac485d6e0b7"
        },
        {
            "id": "431110",
            "title": "9dbb6e6f89674e18adfc7697d9fdce69__fetch.csv",
            "status": {},
            "total": "28780",
            "active": "24960",
            "datecreated": "July 23, 2019, 01:12:42 am",
            "isfolder": "0",
            "optinlist": "0",
            "suppressionlist": "0",
            "suppressionmd5": "0",
            "leased": "0",
            "locked": "0",
            "filesize": "0",
            "liststatsurl": "https://www.softwarelogin.com/liststats.php?id=431110&r=0860d72348568bfec8f42215f1e2a67410cc9a6e"
        }
    ]
}
"""

# https://www.softwarelogin.com/api.php?&area=email&action=getlistdetail&output=json&limit=3&id=431142
coldlist_records = """
{
    "records": "23073",
    "record": [
        {
            "listid": "431142",
            "email": "laurie.armendariz@adventhealth.com",
            "emaildomain": "adventhealth.com",
            "status": "Delivered",
            "emailhash": "115130823634",
            "firstname": "Laurie",
            "lastname": "Armendariz",
            "title": "Director, Patient Experience",
            "company": "Advent Health",
            "industry": "Hospital &amp; Health Care",
            "city": "Winter Springs",
            "state": "Florida",
            "country": "United States of America",
            "profileurl": "https://whoknows.com/users/wp:AYxe954mzq2FksTsRHq3i99Z1wPfcy5EqxDD8Jfe7rRX",
            "emailgrade": {},
            "linkedinurl": {},
            "cleancompany": "Advent Health",
            "url": "chairmanmom.com/adventhealth",
            "domain": "adventhealth.com",
            "isvaliddomain": "TRUE",
            "emailpattern": "{first}.{last}@adventhealth.com",
            "cleanfirstname": "Laurie",
            "cleanlastname": "Armendariz",
            "hasbadchars": "FALSE",
            "gradeforcolumnj": "B",
            "canonicalemail": "laurie.armendariz@adventhealth.com",
            "isrolebased": "NOT-RB",
            "isdisposable": "NOT-DI",
            "domaincountry": "?",
            "domainisfromeu": "?",
            "isfreeemail": "NOT-FREE",
            "ishubspotfreeemail": "NOT-HUBSPOT-FREE",
            "clickts": {},
            "viewts": {},
            "clickip": {},
            "viewip": {},
            "emailid": "1",
            "engagementscore": "0",
            "softbouncecount": "0",
            "debugreason": {}
        },
        {
            "listid": "431142",
            "email": "erik.melville@adventhealth.com",
            "emaildomain": "adventhealth.com",
            "status": "Delivered",
            "emailhash": "257095483130",
            "firstname": "Erik",
            "lastname": "Melville",
            "title": "Medical Assistant",
            "company": "Advent Health Group",
            "industry": "Medical Practice",
            "city": "Lake Worth",
            "state": "Florida",
            "country": "United States of America",
            "profileurl": "https://whoknows.com/users/wp:Fi7UbExALeEa1TgUSvd1mxYjFhDz9eNM9P7CFCxQ4CC6",
            "emailgrade": {},
            "linkedinurl": {},
            "cleancompany": "Advent Health",
            "url": "chairmanmom.com/adventhealth",
            "domain": "adventhealth.com",
            "isvaliddomain": "TRUE",
            "emailpattern": "{first}.{last}@adventhealth.com",
            "cleanfirstname": "Erik",
            "cleanlastname": "Melville",
            "hasbadchars": "FALSE",
            "gradeforcolumnj": "B",
            "canonicalemail": "erik.melville@adventhealth.com",
            "isrolebased": "NOT-RB",
            "isdisposable": "NOT-DI",
            "domaincountry": "?",
            "domainisfromeu": "?",
            "isfreeemail": "NOT-FREE",
            "ishubspotfreeemail": "NOT-HUBSPOT-FREE",
            "clickts": {},
            "viewts": {},
            "clickip": {},
            "viewip": {},
            "emailid": "2",
            "engagementscore": "0",
            "softbouncecount": "0",
            "debugreason": {}
        },
        {
            "listid": "431142",
            "email": "bridgette.randolph@adventhealth.com",
            "emaildomain": "adventhealth.com",
            "status": "Delivered",
            "emailhash": "139095390035",
            "firstname": "Bridgette",
            "lastname": "Randolph",
            "title": "Medical Assistant",
            "company": "Advent Health Group",
            "industry": "Education Management",
            "city": "Washington",
            "state": "District of Columbia",
            "country": "United States of America",
            "profileurl": "https://whoknows.com/users/wp:BbCaSpqcbBYdYkgxHmsrs7K1mFyQw8XgAVQVyY3xmHsd",
            "emailgrade": {},
            "linkedinurl": {},
            "cleancompany": "Advent Health",
            "url": "chairmanmom.com/adventhealth",
            "domain": "adventhealth.com",
            "isvaliddomain": "TRUE",
            "emailpattern": "{first}.{last}@adventhealth.com",
            "cleanfirstname": "Bridgette",
            "cleanlastname": "Randolph",
            "hasbadchars": "FALSE",
            "gradeforcolumnj": "B",
            "canonicalemail": "bridgette.randolph@adventhealth.com",
            "isrolebased": "NOT-RB",
            "isdisposable": "NOT-DI",
            "domaincountry": "?",
            "domainisfromeu": "?",
            "isfreeemail": "NOT-FREE",
            "ishubspotfreeemail": "NOT-HUBSPOT-FREE",
            "clickts": {},
            "viewts": {},
            "clickip": {},
            "viewip": {},
            "emailid": "3",
            "engagementscore": "0",
            "softbouncecount": "0",
            "debugreason": {}
        },
        {
            "listid": "431142",
            "email": "bridgette.randolph@adventhealth.com",
            "emaildomain": "adventhealth.com",
            "status": "Failed",
            "emailhash": "139095390035",
            "firstname": "Bridgette",
            "lastname": "Randolph",
            "title": "Medical Assistant",
            "company": "Advent Health Group",
            "industry": "Education Management",
            "city": "Washington",
            "state": "District of Columbia",
            "country": "United States of America",
            "profileurl": "https://whoknows.com/users/wp:BbCaSpqcbBYdYkgxHmsrs7K1mFyQw8XgAVQVyY3xmHsd",
            "emailgrade": {},
            "linkedinurl": {},
            "cleancompany": "Advent Health",
            "url": "chairmanmom.com/adventhealth",
            "domain": "adventhealth.com",
            "isvaliddomain": "TRUE",
            "emailpattern": "{first}.{last}@adventhealth.com",
            "cleanfirstname": "Bridgette",
            "cleanlastname": "Randolph",
            "hasbadchars": "FALSE",
            "gradeforcolumnj": "B",
            "canonicalemail": "bridgette.randolph@adventhealth.com",
            "isrolebased": "NOT-RB",
            "isdisposable": "NOT-DI",
            "domaincountry": "?",
            "domainisfromeu": "?",
            "isfreeemail": "NOT-FREE",
            "ishubspotfreeemail": "NOT-HUBSPOT-FREE",
            "clickts": {},
            "viewts": {},
            "clickip": {},
            "viewip": {},
            "emailid": "3",
            "engagementscore": "0",
            "softbouncecount": "0",
            "debugreason": {}
        }
    ]
}
"""

# https://www.softwarelogin.com/api.php?&area=email&action=getresultsendsingleemail&output=json&id=6410938
single_email = """
{
    "id": "6410938",
    "email": "chris+20180918@whoknows.com",
    "sendstatus": {},
    "emailstatus": "Delivered",
    "emailtype": "Quick Email",
    "debugreason": "Done sending to chris+20180918@whoknows.com @IP:74.125.128.26",
    "views": "1",
    "clicks": "0",
    "optout": "0",
    "startdate": "December 31, 1969, 06:00:00 pm",
    "enddate": "September 20, 2018, 12:17:29 am"
}
"""

create_message = """
{
    "success": "Messaged Added",
    "id": "182193"
}
"""

message = """
{
    "records": "1",
    "message": {
        "id": "182193",
        "title": "test",
        "datecreated": "July 23, 2019, 07:01:40 pm",
        "numberoftimesused": "0",
        "datelastused": "Never",
        "locked": "0",
        "isfolder": "0",
        "parentid": "0"
    }
}
"""
message_detail = """
{
    "message": {
        "id": "182193",
        "title": "test",
        "datecreated": "July 23, 2019, 07:01:40 pm",
        "numberoftimesused": "0",
        "datelastused": "Never",
        "locked": "0",
        "htmlmsg": "n/a</body></html>",
        "textmsg": "n/a"
    }
}
"""
messages = """
{
    "records": "1291",
    "message": [
        {
            "id": "182193",
            "title": "test",
            "datecreated": "July 23, 2019, 07:01:40 pm",
            "numberoftimesused": "0",
            "datelastused": "Never",
            "locked": "0",
            "isfolder": "0",
            "parentid": "0"
        },
        {
            "id": "182159",
            "title": "WKVIP_X2AI_Employer_20190708",
            "datecreated": "July 23, 2019, 01:06:00 am",
            "numberoftimesused": "0",
            "datelastused": "Never",
            "locked": "0",
            "isfolder": "0",
            "parentid": "0"
        },
        {
            "id": "182158",
            "title": "WK_VIP_Bricleir_Innovation_Execs_20190709",
            "datecreated": "July 23, 2019, 01:02:48 am",
            "numberoftimesused": "1",
            "datelastused": "July 23, 2019, 06:00:31 am",
            "locked": "0",
            "isfolder": "0",
            "parentid": "0"
        },
        {
            "id": "182156",
            "title": "WKVIP_JisekiHealth_SMBs_20190717",
            "datecreated": "July 22, 2019, 04:28:08 pm",
            "numberoftimesused": "1",
            "datelastused": "July 22, 2019, 06:01:32 pm",
            "locked": "0",
            "isfolder": "0",
            "parentid": "0"
        },
        {
            "id": "182141",
            "title": "WK_VIP_CitizensCapital_20190717",
            "datecreated": "July 22, 2019, 02:46:59 am",
            "numberoftimesused": "1",
            "datelastused": "July 22, 2019, 06:01:37 am",
            "locked": "0",
            "isfolder": "0",
            "parentid": "0"
        },
        {
            "id": "182140",
            "title": "WKVIP_X2AI_Employer_20190717",
            "datecreated": "July 22, 2019, 12:47:17 am",
            "numberoftimesused": "1",
            "datelastused": "July 22, 2019, 06:01:29 am",
            "locked": "0",
            "isfolder": "0",
            "parentid": "0"
        },
        {
            "id": "182137",
            "title": "WKVIP_JisekiHealth_SMBs_20190708",
            "datecreated": "July 21, 2019, 05:51:35 pm",
            "numberoftimesused": "0",
            "datelastused": "Never",
            "locked": "0",
            "isfolder": "0",
            "parentid": "0"
        },
        {
            "id": "182134",
            "title": "WK_VIP_CitizensCapital_20190708",
            "datecreated": "July 21, 2019, 01:09:17 am",
            "numberoftimesused": "0",
            "datelastused": "Never",
            "locked": "0",
            "isfolder": "0",
            "parentid": "0"
        },
        {
            "id": "182133",
            "title": "WKVIP_JisekiHealth_SMBs_20190717",
            "datecreated": "July 20, 2019, 04:31:30 pm",
            "numberoftimesused": "1",
            "datelastused": "July 21, 2019, 08:02:41 am",
            "locked": "0",
            "isfolder": "0",
            "parentid": "0"
        },
        {
            "id": "182129",
            "title": "WK_VIP_CitizensCapital_20190717",
            "datecreated": "July 20, 2019, 02:53:26 am",
            "numberoftimesused": "1",
            "datelastused": "July 21, 2019, 09:08:35 am",
            "locked": "0",
            "isfolder": "0",
            "parentid": "0"
        }
    ]
}
"""
