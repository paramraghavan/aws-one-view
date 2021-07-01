
function getHeader(rows) {
    var arrayHeader = [];
    if (rows.list.length > 0) {
        var temp = rows.list[0].split(',');
        headerLen = temp.length;
        if (headerLen > 0) {
            for (i = 0; i < headerLen; i++) {
                arrayHeader.push({ title: temp[i] });
            }
        }
    }
    return arrayHeader;
}

// set hdr count to 0,
function getTableRows(rows, startRow) {
    var arrayOfRows = [];
    for (var i = startRow; i < rows.list.length; i++) {
        var temp = rows.list[i].split(',');
            arrayOfRows.push(temp);
    }
    return arrayOfRows;
}

function postBatchJobInfoReq(oFormElement, element) {
  var xhr = new XMLHttpRequest();
  xhr.onload = function(e) {
    var jsonResponseTxt = xhr.responseText;
    done();

    var jsonResponse = JSON.parse(jsonResponseTxt);
    if(element == 'batchlog' && xhr.status == 200) {
        $('#'.concat(element)).empty();
        console.log('jsonResponse : ' + jsonResponse);
        var arrayLength = jsonResponse.list.length;
        if( arrayLength > 0 ) {
            headerRow = getHeader(jsonResponse)
            console.log(headerRow)
            tableRows = getTableRows(jsonResponse, 1)
            populateTable("1", tableRows, headerRow)
            msg = (arrayLength -1) + " Matching rows found"
            alert(msg);
            $('#'.concat(element)).empty();
            $('#'.concat(element)).append(msg);

        } else {
            msg ='No matching execution jobs found.'
            alert(msg);
            $('#'.concat(element)).empty();
            $('#'.concat(element)).append(msg);
        }
    } else {
        var msg = jsonResponse.list[0];
    	if (xhr.status == 400 || xhr.status == 500 ) {
            done();
            msg = msg + ", Status = " + xhr.status;
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

var statusMap = new Map()

statusMap.set('SUBMITTED', '#33b5e5')
statusMap.set('FAILED', '#BE0C29')
statusMap.set('RUNNABLE', '#F89B47')
statusMap.set('RUNNING', '#F89B47')
statusMap.set('STARTING', '#F89B47')
statusMap.set('SUCCEEDED', '#1D9610')
statusMap.set('PENDING', '#2ECACD')


function populateTable(tabNbr, array, arrayHeader) {
    setupGridPlaceHolder(tabNbr, array, arrayHeader);
    table = $('#example'.concat(tabNbr)).dataTable({
        "lengthMenu": [[25, 50, -1], [25, 50, "All"]],
        "dom": 'Bfrtip',
        "buttons": ["pageLength", "csv", "excel"],
        "data": array,
        "columns": arrayHeader,
        deferRender: true,
        "searching": true,
        scrollY: 800,
        scrollX: "100%",
        scrollCollapse: true,
        scroller: true,
        sort: true,
        order:[[0,'asc'], [1, "desc"]],
        "rowCallback": function (row, data, index) {
            //$(row).addClass(data[data.length-1].toLowerCase());
            $(row).css('color', statusMap.get(data[data.length-1]));
            //$(row).find('td:eq('.concat(4, ')')).addClass('hasmenu');
        },

    });

    $('.dataTable ').on('dblclick', 'tbody tr', function() {
       job_id =this.childNodes[4].innerText
       //alert("job id: " + job_id)
       //get textContent of the TD
       //console.log('TD cell textContent : ', this.textContent)
       getBatchJobDetail(job_id)
    })

     $(document).contextmenu({
        delegate: ".dataTable td:nth-child(5)",
        menu: [
          {title: "Download", cmd: "download"},
          {title: "About", cmd: "about"}
        ],
        select: function(event, ui) {
            switch(ui.cmd){
                case "download":
                    //$(ui.target).parent().remove();
                    var job_id =ui.target.context.innerText;
                    var start_time = ui.target.context.parentElement.cells[1].innerText;
                    var stop_time = ui.target.context.parentElement.cells[2].innerText;
                    var element = 'batchlog';
                    document.getElementById(element).innerHTML = ''
                    var xhr = new XMLHttpRequest();
                    xhr.open("POST", "/getbatchjoblogs", true);
                    xhr.responseType = "blob";

                    xhr.onreadystatechange = function() {
                      console.log(xhr.readyState)
                      console.log(xhr.status)
                     if(xhr.status == 200 && xhr.readyState==4) {
                          const blob = new Blob([xhr.response]);
                          const url = window.URL.createObjectURL(blob);
                          const link = document.createElement('a')
                          link.href = url
                          link.download = element.concat(job_id).concat('.zip')
                          link.click()
                          document.getElementById(element).innerHTML = 'Success';
                        setTimeout(() => {
                            window.URL.revokeObjectURL(url);
                            link.remove();
                        }, 100);
                      } else {
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
                    formData.append("job_id", job_id);
                    formData.append("start_time", start_time);
                    formData.append("stop_time", stop_time);
                    xhr.open("POST", "/getbatchjoblogs");
                    loading();
                    xhr.send(formData);
                    return false;
                    break;
                case "about":
                    job_id =ui.target.context.innerText
                    alert(job_id);
                    getBatchJobDetail(job_id);
                    break;
            }
        },
        beforeOpen: function(event, ui) {
            var $menu = ui.menu,
                $target = ui.target
            ui.menu.zIndex(0);
        }
      });
}


// setup the table inside the grid placeholder
// if its krd back add the footer and extra column for row totals
function setupGridPlaceHolder(tabNbr) {
    var grid = "grid".concat(tabNbr);
    var gridId = "#grid".concat(tabNbr);
    var coltab = "coltab".concat(tabNbr);
    var coltabId = "#coltab".concat(tabNbr);

    $(gridId).remove();
    var divTag = '<div class="container-fluid" id="'.concat(grid, '"></div>');
    //$(coltab).append('<div class="container-fluid" id="grid1" ></div>');
    $(coltabId).append(divTag);
    $(gridId).html('<table class="table table-bordered table-hover display compact cell-border" cellpadding="0" cellspacing="0" border="0" class="display" id="example'.concat(tabNbr, '" style="width:100%"></table>'));
}


function getBatchJobDetail(job_id) {
 element = 'batchlog'
  var xhr = new XMLHttpRequest();
  xhr.onload = function(e) {
    var jsonResponseTxt = xhr.responseText;
    done();
    var msg = JSON.parse(jsonResponseTxt);
    msg = JSON.stringify(msg.list, null, 2);
    if(xhr.status == 200) {
    }
    else {
    	if (xhr.status == 400 || xhr.status == 500 ) {
            msg = msg + ", Status = " + xhr.status;
       }
    }
    alert(msg);
    done();
    $('#'.concat(element)).empty();
    $('#'.concat(element)).append(msg);
  }

    xhr.onerror = function () { // only triggers if the request couldn't be made at all
        done();
        alert('Unable to read .', req);
    };

  var formData = new FormData();
  formData.append("job_id", job_id)
  xhr.open('POST', "getbatchjobdetails");
  loading();
  xhr.send(formData);
  return false;
}
