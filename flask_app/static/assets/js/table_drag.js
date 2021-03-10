var isIE11 = !!window.MSInputMethodContext && !!document.documentMode;
function listenerDragStart(e) {
	e.dataTransfer.effectAllowed = 'move';
	e.dataTransfer.setData('text', $(this).text());

	if (!isIE11) {
		//Create column's container
		var dragGhost = document.createElement("table");
		dragGhost.classList.add("tableGhost");
		dragGhost.classList.add("table-bordered");
		//in order tor etrieve the column's original width
		var srcStyle = document.defaultView.getComputedStyle(this);
		dragGhost.style.width = srcStyle.getPropertyValue("width");
		
		//Create head's clone
		var theadGhost = document.createElement("thead");
		var thisGhost = this.cloneNode(true);
		thisGhost.style.backgroundColor = "red";
		theadGhost.appendChild(thisGhost);
		dragGhost.appendChild(theadGhost);

		var srcTxt = $(this).text();
		var srcIndex = $("th:contains(" + srcTxt + ")").index() + 1;
		//Create body's clone
		var tbodyGhist = document.createElement("tbody");
		$.each($('.table tr td:nth-child(' + srcIndex + ')'), function (i, val) {
			var currentTR = document.createElement("tr");
			var currentTD = document.createElement("td");
			currentTD.innerText = $(this).text();
			currentTR.appendChild(currentTD);
			tbodyGhist.appendChild(currentTR);
		});
		dragGhost.appendChild(tbodyGhist);
		
		//Hide ghost
		dragGhost.style.position = "absolute";
		dragGhost.style.top = "-1500px";
		
		document.body.appendChild(dragGhost);
		e.dataTransfer.setDragImage(dragGhost, 0, 0);
	}
}

function listenerDragOver(e) {
	if (e.preventDefault) {
		e.preventDefault();
	}
	e.dataTransfer.dropEffect = 'move';
	return false;
}

function listenerDragEnter(e) {
	this.classList.add('over');
}

function listenerDragLeave(e) {
	this.classList.remove('over');
}

function listenerDrop(e) {
	if (e.preventDefault) {
		e.preventDefault();
	}
	if (e.stopPropagation) {
		e.stopPropagation();
	}

	var srcTxt = e.dataTransfer.getData('text');
	var destTxt = $(this).text();
	if (srcTxt != destTxt) {
		var dragSrcEl = $(".table th:contains(" + srcTxt + ")");
		var srcIndex = dragSrcEl.index() + 1;
		var destIndex = $("th:contains(" + destTxt + ")").index() + 1;
		dragSrcEl.insertAfter($(this));
		$.each($('.table tr td:nth-child(' + srcIndex + ')'), function (i, val) {
			var index = i + 1;
			$(this).insertAfter($('.table tr:nth-child(' + index + ') td:nth-child(' + destIndex + ')'));
		});
	}
	return false;
}

function listenerDragEnd(e) {
	var cols = document.querySelectorAll('th');
	[].forEach.call(cols, function (col) {
		col.classList.remove('over');
		col.style.opacity = 1;
	});
}

$(document).ready(function () {
	var cols = document.querySelectorAll('th');
	[].forEach.call(cols, function (col) {
		col.addEventListener('dragstart', listenerDragStart, false);
		col.addEventListener('dragenter', listenerDragEnter, false);
		col.addEventListener('dragover', listenerDragOver, false);
		col.addEventListener('dragleave', listenerDragLeave, false);
		col.addEventListener('drop', listenerDrop, false);
		col.addEventListener('dragend', listenerDragEnd, false);
	});
});