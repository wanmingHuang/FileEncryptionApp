function draw_plots(table_index) {
    console.log(table_index, '!!!');
    // TODO: 
    $.ajax({
        type: "POST",
        contentType: "application/json;charset=utf-8",
        url: "collect_plot_data",
        traditional: "true",
        data: JSON.stringify({'table_index': table_index}),
        dataType: "json",
        success: function (data) {
            draw(data.raw, "#rawGraph");
            draw(data.encoded, "#encodedGraph");
        }
    });

}

function draw(data, tag_name) {
    // remove previous plot
    const myNode = document.getElementById(tag_name);
    if (myNode != null) {
        while (myNode.firstChild) {
            myNode.removeChild(myNode.lastChild);
        }
    }

    data = JSON.parse(data);

    var margin = {top: 50, right: 0, bottom: 400, left: 0}
    width = window.innerWidth - margin.left - margin.right // Use the window's width 
    height = window.innerHeight - margin.top - margin.bottom; // Use the window's height

    var column_names = Object.keys(data);

    // The number of datapoints
    var n = Object.keys(data[column_names[0]]).length;

    // 5. X scale will use the index of our data
    var xScale = d3.scaleLinear()
        .domain([0, n-1]) // input
        .range([0, width]); // output
    
    // collect min and max value for y axis
    var min = data[column_names[0]][0];
    var max = data[column_names[0]][0];
    var i;
    var d;
    for (i = 0; i < column_names.length; i++) {
        var column_name = column_names[i];
        for (d = 0; d < n; d++) {
            var value = parseFloat(data[column_name][d]);
            // console.log(value, typeof value, min, max, value < min, value > max);
            if (value < min) min = value;
            if (value > max) max = value;
        }
    }
    var yScale = d3.scaleLinear().domain([min, max]).range([height, 0])

    // 7. d3's line generator
    var line = d3.line()
        .x(function(d, i) { return xScale(i); }) // set the x values for the line generator
        .y(function(d) { return yScale(d.y); }) // set the y values for the line generator 
        .curve(d3.curveMonotoneX) // apply smoothing to the line
    
    // 8. An array of objects of length N. Each object has key -> value pair, the key being "y" and the value is a random number

    // clear all previous drawing
    d3.select(tag_name).selectAll("*").remove();

    // 1. Add the SVG to the page and employ #2
    var svg = d3.select(tag_name).append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
    .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

    // 3. Call the x axis in a group tag
    svg.append("g")
        .attr("class", "x axis")
        .attr("transform", "translate(0," + height + ")")
        .call(d3.axisBottom(xScale)); // Create an axis component with d3.axisBottom

    // 4. Call the y axis in a group tag
    svg.append("g")
        .attr("class", "y axis")
        .call(d3.axisLeft(yScale)); // Create an axis component with d3.axisLeft
    
    var i;
    var legend_height = 0;
    var colors = ['#ff6384', '#36a2eb', '#cc65fe', '#ffce56', "#69b3a2"];
    for (i=0; i < column_names.length; i++) {
        var column_name = column_names[i];
        var dataset = d3.range(n).map(function(d) { return {"y": parseFloat(data[column_name][d]) } })
        // 9. Append the path, bind the data, and call the line generator 
        svg.append("path")
            .datum(dataset) // 10. Binds data to the line 
            .attr("fill", "none")
            .attr("stroke", colors[i])
            .attr("stroke-width", 1.5)
            .attr("class", "line") // Assign a class for styling 
            .attr("d", line); // 11. Calls the line generator 

        // add legend
        svg.append("circle").attr("cx",0).attr("cy",legend_height).attr("r", 6).style("fill", colors[i])
        svg.append("text").attr("x", 0).attr("y", legend_height).text(column_name).style("font-size", "15px").attr("alignment-baseline","middle")
        legend_height += 0.02*window.innerHeight;
    }

}