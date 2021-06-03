

import requests
import json
import csv
import datetime 

ptoList =[]
today = datetime.date.today()
yesterday = today - datetime.timedelta(1)

# create a date range in RFC3339 format based on yesterday to today
rfctoday = str(today) + "T00:00:00Z"
rfcyesterday = str(yesterday) + "T00:00:00Z"

url = "https://api.samsara.com/fleet/vehicles/stats/history"

params = {
    "startTime":rfcyesterday,
    "endTime":rfctoday,
    #ensure the customer is using auxInput1 with their reverse lights to capture reversals.  Change to another auxInput if not.
    "types":"auxInput1", 
    #to get odometer at the moment the Pto is triggered on or off.  gps is for location reverse lookup
    "decorations":"gps, obdOdometerMeters"} 

headers = {
    "Accept": "application/json",
    "Authorization": "Bearer [insert token here]" #Replace with API Token
}

#preparing for pagination, will continue to request until reaches the end of loop and value is FALSE
hasNextPage = True
while hasNextPage:
    #capture response and format as JSON
    response = requests.request("GET", url, headers=headers, params=params).json()

    if response["data"]:
        #Loop to access vehicles and capture vehicle name 
        for x in range(len(response["data"])):
            #Loop to access auxInput1 entries.  Reverse light must be set to auxInput1 
            for y in range(len(response["data"][x]["auxInput1"])):
                #only capture if auxInput1 has data
                if response["data"][x]["auxInput1"][y]["value"]==True:
                    #only capture if obdOdometerMeters has data
                    if response["data"][x]["auxInput1"][y]["decorations"]["obdOdometerMeters"]:
                        #the loop finds the True (on) value of auxInput1 and the value after, which will be false (off).  Condition to keep loop from going over last data index
                        if y+1>=len(response["data"][x]["auxInput1"]):
                            break
                        else:
                            #get odometer value when PTO is on
                            ptoOnDistance = response["data"][x]["auxInput1"][y]["decorations"]["obdOdometerMeters"]["value"]
                            #get odometer value when PTO is off, the next state in the list
                            ptoOffDistance = response["data"][x]["auxInput1"][y+1]["decorations"]["obdOdometerMeters"]["value"]
                            distance = ptoOffDistance - ptoOnDistance
                            #convert meters to feet
                            distance = int(distance * 3.28084)
                            #remove any 0 entries.  If 0 occurs, there was no movement in the vehicle and most likely a PTO false positive
                            if distance > 0 :
                                #get all data
                                vehicleName = response["data"][x]["name"]
                                location = str(response["data"][x]["auxInput1"][y]["decorations"]["gps"]["reverseGeo"]["formattedLocation"])
                                trueTime = response["data"][x]["auxInput1"][y]["time"]
                                falseTime = response["data"][x]["auxInput1"][y+1]["time"]
                                ptoTrue = response["data"][x]["auxInput1"][y]["value"]
                                ptoFalse = response["data"][x]["auxInput1"][y+1]["value"]
                                #convert to datetime so time zone can be adjusted from UTC
                                convertedTrue = datetime.datetime.strptime((trueTime[:-1]), '%Y-%m-%dT%H:%M:%S')
                                convertedFalse = datetime.datetime.strptime((falseTime[:-1]), '%Y-%m-%dT%H:%M:%S')
                                trueEDT = str(convertedTrue - datetime.timedelta(hours=4))
                                falseEDT = str(convertedFalse - datetime.timedelta(hours=4))
                                #create a row in a new list for the data that's relevant to this report with pagination
                                ptoList.append([vehicleName,trueEDT, ptoTrue, falseEDT, ptoFalse, location, distance])

    hasNextPage = response["pagination"]["hasNextPage"]
    print(hasNextPage) #checking if pagination is done correctly
    params["after"] = response["pagination"]["endCursor"]

#Sort by the largest difference in distance captured from obdOdometerMeters
ptoSorted = sorted(ptoList,key=lambda l:l[6], reverse=True)

# Create a CSV based on the caputred rows
with open(str(yesterday) + ".csv", 'w') as csvfile: #comment during testing
# with open("ptoTesting.csv", 'w') as csvfile: #comment during deployment
    writer = csv.writer(csvfile)
    writer.writerow(['vehicleName', 'ptoTrue', 'ptoFalse', 'address', 'distance (ft)'])
    for rows in ptoSorted:
        #check rows, also includes additional info that isn't in the CSV for debugging
        print(rows) 
        #accessing the list's entry to write each column's worth of data.  Can be done better with dictionaries vs lists.
        writer.writerow([
            rows[0],
            rows[1],
            rows[3],
            rows[5],
            rows[6],
            ])
