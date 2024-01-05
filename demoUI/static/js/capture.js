let autostart=true
autostart=false

let flipVertically=false
let flipHorizontally=false

let groupLabels= [ 'centering', 'corners', 'edges', 'surface'  ]
let hiddenLabels= [ 'imgname','Unnamed: 0' ,'art.style','cardmarket.prices.averageSellPrice']
let labelNames=[
  {'oldName':'name'               ,'newName':'name'             ,'class':'bold'},
  {'oldName':'rarity'             ,'newName':'rarity'           ,'class':'bold'},
  {'oldName':'id'                 ,'newName':'Set & Card #'     ,'class':'bold'},
  {'oldName':'centering'          ,'newName':'centering'        ,'class':''},
  {'oldName':'corners'            ,'newName':'corners'          ,'class':''},
  {'oldName':'edges'              ,'newName':'edges'            ,'class':''},
  {'oldName':'surface'            ,'newName':'surface'          ,'class':''},
  {'oldName':'average'            ,'newName':'Grade'            ,'class':''},
  {'oldName':'recent.sale.price'  ,'newName':'Estimated Value'  ,'class':'bold'},
  {'oldName':'sold.at'            ,'newName':'Recently Sold On' ,'class':'bold'}
]


var reset= function(){
  imgFile=undefined

  capturedImage = document.querySelector(".staticImage img");
  capturedImage.src=''

  capturedImageBlock = document.querySelector(".staticImage");
  capturedImageBlock.classList.add('hidden')

  const context = canvas.getContext('2d');
  context.clearRect(0, 0, canvas.width, canvas.height);

  resetResults()
}

var resetResults = function(){
  resultText= document.querySelector('.resultPanel textarea')
  resultText.value=''

  referenceImage=  document.querySelector('.referenceImage img')
  referenceImage.src=''

  cardInfoPanel=  document.querySelector('.cardInfoPanel')
  cardInfoPanel.classList.add('hidden')

  referenceImageBlock=  document.querySelector('.referenceImage')
  referenceImageBlock.classList.add('hidden')

  cardInfoPanel=  document.querySelector('.cardInfoPanel')
  detailTemplate=  document.querySelectorAll('.cardInfoPanel .detail.added')
  for(const detail of [...detailTemplate]){
    detail.remove()
  }
}

var stop = function() {
  cameraFeedBlock=  document.querySelector('.canvasPreview')
  cameraFeedBlock.classList.add('hidden')

  var stream = video.srcObject;
  if (stream==null)
    return
  var tracks = stream.getTracks();

  for (var i = 0; i < tracks.length; i++) {
    var track = tracks[i];
    track.stop();
  }

  video.srcObject = null;
}

var start = function(){
  resetResults()
  cameraFeedBlock=  document.querySelector('.canvasPreview')
  cameraFeedBlock.classList.remove('hidden')

	var video = document.getElementById('video'),
	 vendorUrl = window.URL || window.webkitURL;

	if (navigator.mediaDevices.getUserMedia) {
		navigator.mediaDevices.getUserMedia({ 
    //video: true
    video: {
        width: { ideal: 4096 },
        height: { ideal: 2160 } 
    } 
    })
		.then(function (stream) {
		  video.srcObject = stream;
                    requestAnimationFrame(renderFrame())

    var videoSize = { width: video.videoWidth, height: video.videoHeight };
    console.log(videoSize)
		}).catch(function (error) {
      //alert('couldn\'t open camera, please close this window and try again')
		  //console.log(error);
		  //console.log("Something went wrong!");
		});
	}
}
var canvas
var img
var imgFile
var resultText
$(function() {
    canvas = document.querySelector("canvas");
    img = document.querySelector(".staticImage img");
    resultText= document.querySelector('.resultPanel textarea')
 
    if (autostart)
        start();
});

function calculateSize(srcSize, dstSize) {
    var srcRatio = srcSize.width / srcSize.height;
    var dstRatio = dstSize.width / dstSize.height;
    if (dstRatio > srcRatio) {
      return {
        width:  dstSize.height * srcRatio,
        height: dstSize.height
      };
    } else {
      return {
        width:  dstSize.width,
        height: dstSize.width / srcRatio
      };
    }
  }
function renderFrame() {
  // re-register callback
  requestAnimationFrame(renderFrame);
  // set internal canvas size to match HTML element size
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
 

  //canvas.width = canvas.scrollWidth;
  //canvas.height = canvas.scrollHeight;
  if (video.readyState === video.HAVE_ENOUGH_DATA) {
    // scale and horizontally center the camera image
    var videoSize = { width: video.videoWidth, height: video.videoHeight };
    var canvasSize = { width: canvas.width, height: canvas.height };
    var renderSize = calculateSize(videoSize, canvasSize);
    var xOffset = (canvasSize.width - renderSize.width) / 2;
    context=canvas.getContext('2d')
    //context.drawImage(video, xOffset, 0, renderSize.width, renderSize.height);

    if (flipHorizontally){
      context.translate(renderSize.width,0);
      // scaleX by -1; to flip horizontally
      context.scale(-1,1);
    }
    if (flipVertically){
      context.translate(0,renderSize.height);
      context.scale(1,-1);
    }
    context.drawImage(video, xOffset, 0, renderSize.width, renderSize.height);
    context.setTransform(1,0,0,1,0,0);

    context.beginPath();
    //context.rect(80, 20, 150, 100);
    context.rect(squareLimits[0],squareLimits[1], squareLimits[2], squareLimits[3]);
    context.stroke();
  }
}

var save = function(){
  resetResults()
    capturedImageBlock = document.querySelector(".staticImage");
    capturedImageBlock.classList.remove('hidden')

    //get image without overlapped elements
    //canvas.width = video.videoWidth;
    //canvas.height = video.videoHeight;
    //canvas.getContext("2d").drawImage(video, 0, 0);

    // Other browsers will fall back to image/png
    imgFile=canvas.toDataURL("image/webp");
    img.src = imgFile;
};

/* Old Code */
/*
var identify = function(){
    resetResults()
    referenceImageBlock=  document.querySelector('.referenceImage')
    referenceImageBlock.classList.remove('hidden')

    cardInfoPanel=  document.querySelector('.cardInfoPanel')
    cardInfoPanel.classList.remove('hidden')

    resultText.value=''
    stop()
    //console.log(imgFile)
    request =new XMLHttpRequest()
    request.open("POST", "/identifyImage", true);
    //request.setRequestHeader('api-key', 'your-api-key');
    request.setRequestHeader("Content-type", "application/json");
    parameters={
        image:imgFile
    }
    //console.log(parameters)
    request.send(JSON.stringify(parameters));
    request.onreadystatechange = function() {
        result=''
        result+='\nready state:'+this.readyState
        result+='\nstatus:'+this.status
        if (this.readyState == 4 && this.status == 200) {
          jsonResult=JSON.parse(request.responseText)
          result+='\nOK'+jsonResult['result']
          if (jsonResult['result']=='ok'){
            fillCardInfo(JSON.parse(request.responseText))
          }
          if (jsonResult['message']!=''){
            alert(jsonResult['message']);
          }
        }
        result+='\n'+request.responseText
        resultText.value=result
        //console.log(this.result)
    };

}
*/

let subtotal=0
let count=0
 
function fillCardInfo(cardInfo, artwork_data){
  /*
  cardInfoPanel=  document.querySelector('.cardInfoPanel')
  groupContainer=  document.querySelector('.cardInfoPanel .groupContainer')
  group=  document.querySelector('.cardInfoPanel .group')
  groupTotal=  document.querySelector('.cardInfoPanel .subtotal')
  subtotal=0
  count=0
  detailTemplate=  document.querySelector('.cardInfoPanel .detail.template')
  normalizedInfo=[]
  for (let keyPair of labelNames){
    if (keyPair['oldName'] in cardInfo["matchedCard"]){
      normalizedInfo.push({
      'label':keyPair['newName'],
      'value':cardInfo["matchedCard"][keyPair['oldName']],
      'class':keyPair['class'],
    }) 
    }
  }
  for (let detail of normalizedInfo){
    addDetail(detailTemplate, detail['label'], detail['value'], cardInfoPanel, detail['class'])
  }
  subtotal=(Math.round(subtotal/count/0.5)*0.5).toString()
  addDetail(detailTemplate, 'grade', subtotal, cardInfoPanel, 'bold')

  referenceImage=  document.querySelector('.referenceImage img')
  referenceImage.src=cardInfo["matchedCardImage"]
  referenceImage.src=cardInfo["artworkImage"]
  */
  cardInfoPanel=  document.querySelector('.cardInfoPanel')
  groupContainer=  document.querySelector('.cardInfoPanel .groupContainer')
  group=  document.querySelector('.cardInfoPanel .group')
  groupTotal=  document.querySelector('.cardInfoPanel .subtotal')

  detailTemplate=  document.querySelector('.cardInfoPanel .detail.template')

  normalizedInfo.push({
    'label':'Name',
    'value':cardInfo['name'],
    'class':,
  })
  normalizedInfo.push({
    'label':'Sell Price',
    'value':cardInfo['averageSellPrice'],
    'class':,
  })

  for (let detail of normalizedInfo){
    addDetail(detailTemplate, detail['label'], detail['value'], cardInfoPanel, detail['class'])
  }

  referenceImage=  document.querySelector('.referenceImage img')
  referenceImage.src=artwork_data
}

function addDetail(detailTemplate, detail, value, cardInfoPanel, classes){
    newDetail=detailTemplate.cloneNode(true)
    newDetail.classList.remove('template')
    newDetail.classList.add('added')
    if (classes!='')
      newDetail.classList.add(classes)
    newDetail.querySelector('.detailLabel').innerText=detail
    newDetail.querySelector('.detailValue').innerText=value
    if (groupLabels.includes(detail)){
      cardInfoPanel.append(groupContainer)

      group.append(newDetail)
      subtotal=subtotal+parseFloat( value )
      count=count+1
    }
    else if(detail=='grade'){
      groupTotal.append(newDetail)
    }
    else if (hiddenLabels.includes(detail)){
      ;//don't show
    }
    else{
      cardInfoPanel.append(newDetail)
    }
}

var analyse = function(){
    request =new XMLHttpRequest()
    request.open("POST", "/analyse", true);
    request.setRequestHeader("Content-type", "application/json");
    parameters={
        parameter:''
    }
    request.send(JSON.stringify(parameters));
    request.onreadystatechange = function() {
        result=''
        result+='\nready state:'+this.readyState
        result+='\nstatus:'+this.status
        if (this.readyState == 4 && this.status == 200) {
          jsonResult=JSON.parse(request.responseText)
          result+='\nOK'+jsonResult['result']
          if (jsonResult['result']=='ok'){
              alert('database was updated successfully');
          }else{
            alert(jsonResult['message'])
          }
        }
        result+='\n'+request.responseText
        console.log(result)
    };
}

function initialize_web_socket() {
	try {
		const host = window.location.host.replace(/:\d+$/, '');
		if (location.protocol == 'https:') {
			socket = new WebSocket("wss://"+host+"/websocket");
		} else {
			//socket = new WebSocket("ws://"+host+"/websocket");
			socket = new WebSocket("ws://"+host+":8080");
		}
		socket.onopen = function() {
			socket.send(JSON.stringify({ token: "jwtcardsortertoken" }));
			console.log("Connected to WebSocket server");

			// Send a message to the server
			//socket.send("Hello, WebSocket server!");
		};

		socket.onmessage = function(event) {
			try{
				console.log("Received message:\n" + event.data.substring(0, 100) + "...");
				//try to parse as json
				jsonResult=JSON.parse(event.data)
				image_b64= jsonResult['frame']
				//jsonResult['frame'] = (image_b64 ? true : false);
				running = jsonResult['running']
				if ('message' in jsonResult && jsonResult['message']){
					console.log(jsonResult['message']);
					console.log(running)
				}

				if (running){
					document.querySelector('.canvasPreview.monitorCanvas').style.background='green';
				}
				else{
					document.querySelector('.canvasPreview.monitorCanvas').style.background='red';
				}

				canvas = document.querySelector('.canvasPreview canvas')
				var ctx = canvas.getContext('2d');
				// Base64-encoded image data
				if (image_b64!=null){
					var base64ImageData = 'data:image/png;base64,' + image_b64;

					// Create an Image object
					var img = new Image();

					// Set the source of the image to the base64 data
					img.src = base64ImageData;

					// When the image is loaded, draw it onto the canvas
					img.onload = function () {
						var aspectRatio = img.width / img.height;

						// Calculate new dimensions to fit within the canvas
						var newWidth = canvas.width;
						var newHeight = canvas.width / aspectRatio;

						// Check if the new height exceeds the canvas height
						if (newHeight > canvas.height) {
							newHeight = canvas.height;
							newWidth = canvas.height * aspectRatio;
						}

						// Calculate position to center the image
						var x = (canvas.width - newWidth) / 2;
						var y = (canvas.height - newHeight) / 2;

						// Draw the image with the new dimensions and position
						ctx.drawImage(img, x, y, newWidth, newHeight);
						//ctx.drawImage(img, 0, 0); // Draw the image at coordinates (0, 0)
					};
				}
        
        //figure out format of values from message
        if (jsonResult['message']=='ok' && jsonResult['message']['cardValues'] !== NULL){
          fillCardInfo(jsonResult['message']['cardValues'], jsonResult['message']['artwork_data'])
        }

				//document.querySelector('#text-source-text').value=document.querySelector('#text-source-text').value +'\n'+ event.data;
				//text_to_questions_preview(false);
				//hideLoadingScreen();
			}
			catch (ex){
				console.log(ex)
			}
		};

		socket.onclose = function() {
			console.log("Connection closed");
			//hideLoadingScreen();
			setTimeout(initialize_web_socket, 1000);
		};

		socket.onerror = function(error) {
			console.error("An error occurred: " + error.message);
			//hideLoadingScreen();
		};
	} catch (ex) {
		console.log(ex);
	}
}


//execute a funciton whe page loads
window.onload = function() {
    initialize_web_socket();
};



