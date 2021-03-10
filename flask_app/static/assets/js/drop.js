function allowDrop(ev) {
    ev.preventDefault();
}
  
function drag(ev) {
    ev.dataTransfer.setData("text", ev.target.id);
}

function drop(ev) {
    ev.preventDefault();
    var data = ev.dataTransfer.getData("text");
    // console.log(data, ev.target, '!!!')
    // ev.target.appendChild(document.getElementById(data));
    ev.target.value = ev.target.value + ' ' + data
}