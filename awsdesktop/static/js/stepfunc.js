var taskStatus = {
    "SUCCEEDED" : "bar-succeeded",
    "FAILED" : "bar-failed",
    "RUNNING" : "bar-running",
    "ABORT" : "bar-abort"
};
var taskNames = []
var tasks = []
var gantt;
var minDate;
var maxDate;
var format = "%H:%M";
var timeDomainString = "1day";

function getTimeDiffinHours(startdate, enddate) {
    var diff = startdate.valueOf() - enddate.valueOf();
    //var diffInHours = diff/1000/60/60; // Convert milliseconds to hours
    var diffInHours = diff/1000/60/60; // Convert milliseconds to hours

    return diffInHours
}


function changeTimeDomainSlider(value) {
    this.timeDomainString = timeDomainString;

    format = "%H:%M:%S";
    var diffinhours =  getTimeDiffinHours(getEndDate(), getStartDate())
    var interval = (diffinhours * value)/100
    gantt.timeDomain([ getStartDate(), d3.time.hour.offset(getStartDate(),interval) ]);
    gantt.tickFormat(format);
    gantt.redraw(tasks);
}

function changeTimeDomain(timeDomainString) {
    this.timeDomainString = timeDomainString;
    switch (timeDomainString) {
    case "1hr":
    format = "%H:%M:%S";
    gantt.timeDomain([ d3.time.hour.offset(getEndDate(), -1), getEndDate() ]);
    break;
    case "3hr":
    format = "%H:%M";
    gantt.timeDomain([ d3.time.hour.offset(getEndDate(), -3), getEndDate() ]);
    break;

    case "6hr":
    format = "%H:%M";
    gantt.timeDomain([ d3.time.hour.offset(getEndDate(), -6), getEndDate() ]);
    break;

    case "1day":
    format = "%H:%M";
    gantt.timeDomain([ d3.time.day.offset(getEndDate(), -1), getEndDate() ]);
    break;

    case "1week":
    format = "%a %H:%M";
    gantt.timeDomain([ d3.time.day.offset(getEndDate(), -7), getEndDate() ]);
    break;

    case "actual":
	format = "%a %H:%M";
	gantt.timeDomain([ getStartDate(), getEndDate() ]);
	break;

    default:
    format = "%H:%M"

    }
    gantt.tickFormat(format);
    gantt.redraw(tasks);
}


function getStartDate() {
    var startDate = Date.now();
    if (tasks.length > 0) {
	    startDate = tasks[0].startDate;
    }

    return startDate;
}

function getEndDate() {
    var lastEndDate = Date.now();
    if (tasks.length > 0) {
    lastEndDate = tasks[tasks.length - 1].endDate;
    }

    return lastEndDate;
}

function addTask() {

    var lastEndDate = getEndDate();
    var taskStatusKeys = Object.keys(taskStatus);
    var taskStatusName = taskStatusKeys[Math.floor(Math.random() * taskStatusKeys.length)];
    var taskName = taskNames[Math.floor(Math.random() * taskNames.length)];

    tasks.push({
    "startDate" : d3.time.hour.offset(lastEndDate, Math.ceil(1 * Math.random())),
    "endDate" : d3.time.hour.offset(lastEndDate, (Math.ceil(Math.random() * 3)) + 1),
    "taskName" : taskName,
    "status" : taskStatusName
    });

    changeTimeDomain(timeDomainString);
    gantt.redraw(tasks);
};

function removeTask() {
    tasks.pop();
    changeTimeDomain(timeDomainString);
    gantt.redraw(tasks);
};



function getExecutionAppId(executionArn, description) {
  loading();
  var element = 'executionappid';
     $('#'.concat(element)).empty();
    var download_link = $("<a>");
    download_link.attr("href", "http://localhost:8080/getexecutionappid?executionArn=".concat(executionArn));
    //download_link.attr("href", "javascript:;");
    //download_link.attr("onclick", 'getExecutionAppIdDownload('.concat(executionArn).concat(',').concat(description).concat(')'));
    //download_link.attr("onclick", 'getExecutionAppIdDownload('.concat('"').concat(executionArn).concat('"').concat(',').concat(' "').concat(description).concat('"').concat(')'));
    download_link.attr("title", executionArn);
    download_link.attr("style", 'font-weight:bold;color:black');
    download_link.text("Link To Download execution history log --> ".concat(description));
    download_link.addClass("link");
    $('#'.concat(element)).html(download_link);
    alert(description)
    done();
}

function getExecutionAppIdDownloadUrl(executionArn, description) {
    var download_link = $("<a>");
    download_link.attr("href", "http://localhost:8080/getexecutionappid?executionArn=".concat(executionArn));
    //download_link.attr("href", "javascript:;");
    //download_link.attr("onclick", 'getExecutionAppIdDownload('.concat(executionArn).concat(',').concat(description).concat(')'));
    //download_link.attr("onclick", 'getExecutionAppIdDownload('.concat('"').concat(executionArn).concat('"').concat(',').concat(' "').concat(description).concat('"').concat(')'));
    download_link.attr("title", executionArn);
    download_link.attr("style", 'font-weight:bold;color:black');
    download_link.text("Link To Download execution history log --> ".concat(description));
    download_link.addClass("link");
    return download_link;
}


function postInfojobs(oFormElement, element) {
  var xhr = new XMLHttpRequest();
  xhr.onload = function(e) {
    var jsonResponseTxt = xhr.responseText;
//    alert(jsonResponseTxt);
//    $('#'.concat(element)).empty();
//    $('#'.concat(element)).append(jsonResponseTxt);
    done();
    //var tasks = [{"startDate":new Date("2020-12-01 07:00:00"),"endDate":new Date("2020-12-01 07:08:00"),"taskName":"E Job","status":"FAILED", "description":"Not Implemented"}];
    //"ChathamReconLolClsdDatamart-20201230-054936,FAILED,erm01-devl-edl-hao-chatham-recon-clsd-datamart-rpt-workflow-v01,2020-12-30 00:49:41,2020-12-30 01:23:23,arn:aws:states:us-east-1:742458541136:stateMachine:erm01-devl-edl-hao-chatham-recon-clsd-datamart-rpt-workflow-v01"
    var dictTaskNames = {};
    taskNames = [];
    tasks = [];
    taskAliasName = 1;
    var jsonResponse = JSON.parse(jsonResponseTxt);
    if(element == 'dashlog' && xhr.status == 200) {
        $('#'.concat(element)).empty();
        console.log('jsonResponse : ' + jsonResponse);
        var arrayLength = jsonResponse.list.length;
        if(arrayLength == 0) {
            alert('No match found.')
        }
        //$('#'.concat(element)).empty();
        clearcontent('div-chart-container')
        clearcontent('legend')
        if( arrayLength > 0 ) {
            //value = '';
            //$('#'.concat(element)).append($('<option>').text(value).attr('value', value));
            for (var i = 0; i < arrayLength; i++) {
                var value = jsonResponse.list[i];
                arr = value.split(',');
                dict = {};
                if (!(arr[2] in dictTaskNames)) {
                    dictTaskNames[arr[2]] =  taskAliasName;
                    taskAliasName = taskAliasName + 1;
                }

                dict["startDate"] = new Date(arr[3]);
                dict["endDate"] = new Date(arr[4]);
                dict["taskName"] = dictTaskNames[arr[2]];
                dict["status"] = arr[1];
                dict["description"] = arr[0];
                dict["executionArn"] = arr[5];
                tasks.push(dict);
                //console.log(value);
                //$('#'.concat(element)).append($('<option>').text(value).attr('value', value));
            }

            var table = document.createElement('table');
            for (var key in dictTaskNames) {
                  value = dictTaskNames[key]
                  console.log(key, value);
                  taskNames.push(value);
                  var tr = document.createElement('tr');

                  var td1 = document.createElement('td');
                  var td2 = document.createElement('td');

                  var text1 = document.createTextNode(value);
                  var text2 = document.createTextNode(key);

                  td1.appendChild(text1);
                  td2.appendChild(text2);
                  tr.appendChild(td1);
                  tr.appendChild(td2);

                  table.appendChild(tr);
            }
            document.getElementById("legend").appendChild(table);

            tasks.sort(function(a, b) {
                return a.endDate - b.endDate;
            });
            maxDate = tasks[tasks.length - 1].endDate;
            tasks.sort(function(a, b) {
                return a.startDate - b.startDate;
            });
            minDate = tasks[0].startDate;

            format = "%H:%M";
            timeDomainString = "1day";

            //gantt = d3.gantt().taskTypes(taskNames).taskStatus(taskStatus).tickFormat(format).selector('div-chart').height(450).width(800);
            //var gantt = d3.gantt().taskTypes(taskNames).taskStatus(taskStatus).tickFormat(format).height(450).width(800);
            gantt = d3.gantt().taskTypes(taskNames).taskStatus(taskStatus).selector("#div-chart-container").tickFormat(format).height(1000).width(1800);

            gantt.timeDomainMode("fixed");
            changeTimeDomain(timeDomainString);

            gantt(tasks);
          // end gantt

        }
    } else {
        var msg = jsonResponse.list[0];
    	if (xhr.status == 400 || xhr.status == 500 ) {
            done();
            msg = msg + ", Status = " + xhr.statusText;
    	}
        alert(msg);
        $('#'.concat(element)).empty();
        $('#'.concat(element)).append(msg);
    }
  }

xhr.onerror = function () { // only triggers if the request couldn't be made at all
    done();
    alert('Unable to read .', req);
};

  xhr.open(oFormElement.method, oFormElement.getAttribute("action"));
  var data =  new FormData(oFormElement);
  loading();
  xhr.send(data);
  return false;
}

function clearcontent(elementID) {
    document.getElementById(elementID).innerHTML = "";
}
