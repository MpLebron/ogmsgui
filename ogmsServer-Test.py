"""
Author: DiChen
Date: 2024-09-07 09:26:00
LastEditors: DiChen
LastEditTime: 2024-09-15 02:23:59
"""

# from ogmsServer2 import openModel
import ogmsServer2.openModel as openModel
import httpx

# Test sample data
lists = {
    "LandSlide": {
        "inputBaseTif": "./ogmsServer2/data/baseclip.tif",
        "inputPGATif": "./ogmsServer2/data/PGA.tif",
        "inputIntensityTif": "./ogmsServer2/data/intensity.tif",
    }
}

# run model and download result

taskServer = openModel.OGMSAccess(
    modelName="地震群发滑坡概率评估预警模型",
    token="6U3O1Sy5696I5ryJFaYCYVjcIV7rhd1MKK0QGX9A7zafogi8xTdvejl6ISUP1lEs",
)
result = taskServer.createTask(params=lists)
print(result)
# taskServer.downloadAllData()
 