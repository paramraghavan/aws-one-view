var call_url = 'https://confluence:8443/display/CFERMMRP/HAO+Production+Support+Schedule'
var support_url = 'https://fnma.sharepoint.com/:w:/r/sites/ADM-ERM_CF_PS/ERM/ERM%20APPLICATION%20MANAGEMENT/ERM%20SI/ERM%20DataLake/ERM-AWS%20DataLake/Hedge%20Accounting%20Optimizer/Application%20Documents/HAO%20ops%20manual/operationsManual_v8.2_ERM_EDL_HAO.DOCX?d=w021b0d165f554c3b9f698381cf498efc&csf=1&web=1&e=Gotc5d'

/**
 * ref: http://bl.ocks.org/dk8996/5538271
 * This has been customised
 */

d3.gantt = function() {
    var FIT_TIME_DOMAIN_MODE = "fit";
    var FIXED_TIME_DOMAIN_MODE = "fixed";

    var margin = {
	top : 20,
	right : 40,
	bottom : 20,
	left : 150
    };
    var timeDomainStart = d3.time.day.offset(new Date(),-3);
    var timeDomainEnd = d3.time.hour.offset(new Date(),+3);
    var timeDomainMode = FIT_TIME_DOMAIN_MODE;// fixed or fit
    var taskTypes = [];
    var taskStatus = [];
    var height = document.body.clientHeight - margin.top - margin.bottom-5;
    var width = document.body.clientWidth - margin.right - margin.left-5;

    var tickFormat = "%H:%M";

    var keyFunction = function(d) {
	return d.startDate + d.taskName + d.endDate;
    };

    var rectTransform = function(d) {
	return "translate(" + x(d.startDate) + "," + y(d.taskName) + ")";
    };

    var x = d3.time.scale().domain([ timeDomainStart, timeDomainEnd ]).range([ 0, width ]).clamp(true);

    var y = d3.scale.ordinal().domain(taskTypes).rangeRoundBands([ 0, height - margin.top - margin.bottom ], .1);

    var xAxis = d3.svg.axis().scale(x).orient("bottom").tickFormat(d3.time.format(tickFormat)).tickSubdivide(true)
	    .tickSize(8).tickPadding(8);

    var yAxis = d3.svg.axis().scale(y).orient("left").tickSize(0);

    var initTimeDomain = function() {
	if (timeDomainMode === FIT_TIME_DOMAIN_MODE) {
	    if (tasks === undefined || tasks.length < 1) {
		timeDomainStart = d3.time.day.offset(new Date(), -3);
		timeDomainEnd = d3.time.hour.offset(new Date(), +3);
		return;
	    }
	    tasks.sort(function(a, b) {
		return a.endDate - b.endDate;
	    });
	    timeDomainEnd = tasks[tasks.length - 1].endDate;
	    tasks.sort(function(a, b) {
		return a.startDate - b.startDate;
	    });
	    timeDomainStart = tasks[0].startDate;
	}
    };

    var initAxis = function() {
	x = d3.time.scale().domain([ timeDomainStart, timeDomainEnd ]).range([ 0, width ]).clamp(true);
	y = d3.scale.ordinal().domain(taskTypes).rangeRoundBands([ 0, height - margin.top - margin.bottom ], .1);
	xAxis = d3.svg.axis().scale(x).orient("bottom").tickFormat(d3.time.format(tickFormat)).tickSubdivide(true)
		.tickSize(8).tickPadding(8);

	yAxis = d3.svg.axis().scale(y).orient("left").tickSize(0);
    };

    var selector = 'body';
    function gantt(tasks) {

	initTimeDomain();
	initAxis();

    // Define the div for the tooltip
    var div = d3.select(selector).append("div")
        .attr("class", "tooltip")
        .style("opacity", 0)
        .style("font-size", "large")
        .style("font-weight", "bold")
        .style("color", "black");

	var svg = d3.select(selector)
	.append("svg")
	.attr("class", "chart")
	.attr("width", width + margin.left + margin.right)
	.attr("height", height + margin.top + margin.bottom)
	.append("g")
        .attr("class", "gantt-chart")
	.attr("width", width + margin.left + margin.right)
	.attr("height", height + margin.top + margin.bottom)
	.attr("transform", "translate(" + margin.left + ", " + margin.top + ")");


      var menu = ["Download Logs", "Triage", "Help", "Call", "About"];
      svg.selectAll(".chart")
	 .data(tasks, keyFunction).enter()
	 .append("rect")
	 .attr("rx", 5)
         .attr("ry", 5)
	 .attr("class", function(d){
	     if(taskStatus[d.status] == null){ return "bar";}
	     return taskStatus[d.status];
	     })
	 .attr("y", 0)
     .on("mouseover", function(d) {
        div.transition()
            .duration(200)
            .style("opacity", .9);
        div	.html(d.description)
            .style("left", (d3.event.pageX) + "px")
            .style("top", (d3.event.pageY - 28) + "px")
            .style("width", 600 + "px");
        })
    .on("mouseout", function(d) {
        div.transition()
            .duration(500)
            .style("opacity", 0);
      })
     .on("dblclick",function(d){getExecutionAppId(d.executionArn, d.description) })
	 .attr("transform", rectTransform)
	 .attr("height", function(d) { return y.rangeBand(); })
	 .attr("width", function(d) {
	     return (x(d.endDate) - x(d.startDate));
	     })
     .on('contextmenu', function(d,i) {
           // create the div element that will hold the context menu
           d3.selectAll('.context-menu').data([1])
             .enter()
             .append('div')
             .attr('class', 'context-menu');
           // close menu
           d3.select('body').on('click.context-menu', function() {
             d3.select('.context-menu').style('display', 'none');
             });
           //mod_menu mod_menu.clone();
//           len=menu.length;
//           for(i=0; i < len; i++ ) {
//            value = menu[i].concat(' ').concat(d.description);
//            mod_menu.push(value);
//           };
           // this gets executed when a contextmenu event occurs
           d3.selectAll('.context-menu')
             .html('')
             .append('ul')
             .selectAll('li')
             //.data(menu).enter()
             .data(menu).enter()
             .append('li')
             .on('click' , function(m_d) {
                        //alert(d.description)
                   if(m_d.startsWith('Download')) {
                        var element = 'executionappid';
                        //download_url = '/getexecutionappid?executionArn='.concat(d.executionArn)
                        document.getElementById(element).innerHTML = ''
                        var xhr = new XMLHttpRequest();
                        xhr.open("POST", "/getexecutionappid", true);
                        xhr.responseType = "blob";

                        xhr.onreadystatechange = function() {
                          console.log(xhr.readyState)
                          console.log(xhr.status)
                         if(xhr.status == 200 && xhr.readyState==4) {
                              const blob = new Blob([xhr.response]);
                              const url = window.URL.createObjectURL(blob);

                              const link = document.createElement('a')
                              link.href = url
                              link.download = d.executionArn.concat('.zip')
                              link.click()
                              document.getElementById(element).innerHTML = 'Success';
                            setTimeout(() => {
                                window.URL.revokeObjectURL(url);
                                link.remove();
                            }, 100);
                          }
                          else {
                            if ((xhr.status == 400 || xhr.status == 500 ) && xhr.readyState==4) {
                                done();
                                var msg = blobToString(xhr.response) + ", Status = " + xhr.status;
                                $('#'.concat(element)).empty();
                                $('#'.concat(element)).append(msg);
                                alert(msg);
                            }
                          }
                          done();
                        }
                        var formData = new FormData();
                        formData.append("executionArn", d.executionArn);
                        xhr.open("POST", "/getexecutionappid");
                        loading();
                        xhr.send(formData);
                        return false;
                  }

                    if(m_d.startsWith('Help')) {
                      alert("Help docs goes here");
                      window.open(support_url, "Help", "width=1200,height=900");
                    }
                    if(m_d.startsWith('Call')) {
                     window.open(call_url, "Call", "width=1200,height=900");
                    }
                    if(m_d.startsWith('Triage')) {
                        alert("Triage docs goes here");
                    }
                    if(m_d.startsWith('About')) {
                        msg = "About This Job : \n".concat(d.description)
                        alert(msg);
                    }
                    done();
                    return;

                })
           .text(function(d) { return d; });
           d3.select('.context-menu').style('display', 'none');
           // show the context menu
           d3.select('.context-menu')
             .style('left', (d3.event.pageX - 2) + 'px')
             .style('top', (d3.event.pageY - 2) + 'px')
             .style('display', 'block');
           d3.event.preventDefault();
     });





	 svg.append("g")
	 .attr("class", "x axis")
	 .attr("transform", "translate(0, " + (height - margin.top - margin.bottom) + ")")
	 .transition()
	 .call(xAxis);

	 svg.append("g").attr("class", "y axis").transition().call(yAxis);

	 return gantt;

    };

    gantt.redraw = function(tasks) {

	initTimeDomain();
	initAxis();

        var svg = d3.select("svg");

        var ganttChartGroup = svg.select(".gantt-chart");
        var rect = ganttChartGroup.selectAll("rect").data(tasks, keyFunction);

        rect.enter()
         .insert("rect",":first-child")
         .attr("rx", 5)
         .attr("ry", 5)
	 .attr("class", function(d){
	     if(taskStatus[d.status] == null){ return "bar";}
	     return taskStatus[d.status];
	     })
	 .transition()
	 .attr("y", 0)
	 .attr("transform", rectTransform)
	 .attr("height", function(d) { return y.rangeBand(); })
	 .attr("width", function(d) {
	     return (x(d.endDate) - x(d.startDate));
	     });

        rect.transition()
          .attr("transform", rectTransform)
	 .attr("height", function(d) { return y.rangeBand(); })
	 .attr("width", function(d) {
	     return (x(d.endDate) - x(d.startDate));
	     });

	rect.exit().remove();

	svg.select(".x").transition().call(xAxis);
	svg.select(".y").transition().call(yAxis);

	return gantt;
    };

    gantt.margin = function(value) {
	if (!arguments.length)
	    return margin;
	margin = value;
	return gantt;
    };

    gantt.timeDomain = function(value) {
	if (!arguments.length)
	    return [ timeDomainStart, timeDomainEnd ];
	timeDomainStart = +value[0], timeDomainEnd = +value[1];
	return gantt;
    };

    /**
     * @param {string}
     *                vale The value can be "fit" - the domain fits the data or
     *                "fixed" - fixed domain.
     */
    gantt.timeDomainMode = function(value) {
	if (!arguments.length)
	    return timeDomainMode;
        timeDomainMode = value;
        return gantt;

    };

    gantt.taskTypes = function(value) {
	if (!arguments.length)
	    return taskTypes;
	taskTypes = value;
	return gantt;
    };

    gantt.taskStatus = function(value) {
	if (!arguments.length)
	    return taskStatus;
	taskStatus = value;
	return gantt;
    };

    gantt.width = function(value) {
	if (!arguments.length)
	    return width;
	width = +value;
	return gantt;
    };

    gantt.height = function(value) {
	if (!arguments.length)
	    return height;
	height = +value;
	return gantt;
    };

    gantt.tickFormat = function(value) {
	if (!arguments.length)
	    return tickFormat;
	tickFormat = value;
	return gantt;
    };

    gantt.selector = function(value) {
    if (!arguments.length)
        return selector;
    selector = value;
    return gantt;
    };

    return gantt;
};