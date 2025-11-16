// D3.js horizontal bar chart for monthly view counts
// Expects global variable: monthlyData (from template, in display order)

document.addEventListener('DOMContentLoaded', function() {
    const data = monthlyData;

    // Set up dimensions and margins
    const margin = {top: 50, right: 30, bottom: 50, left: 80};
    const width = 800 - margin.left - margin.right;
    const height = Math.max(400, data.length * 25) - margin.top - margin.bottom;

    // Update SVG height based on data
    d3.select("#chart").attr("height", height + margin.top + margin.bottom);

    // Select SVG and add group element
    const svg = d3.select("#chart")
        .append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`);

    // Create scales
    const x = d3.scaleLinear()
        .domain([0, d3.max(data, d => d.count)])
        .nice()
        .range([0, width]);

    const y = d3.scaleBand()
        .domain(data.map(d => d.month))
        .range([0, height])
        .padding(0.2);

    // Add X axis at top
    svg.append("g")
        .call(d3.axisTop(x));

    // Add Y axis
    svg.append("g")
        .call(d3.axisLeft(y));

    // Add X axis label at top
    svg.append("text")
        .attr("text-anchor", "middle")
        .attr("x", width / 2)
        .attr("y", -35)
        .text("View Count");

    // Add Y axis label
    svg.append("text")
        .attr("text-anchor", "middle")
        .attr("transform", "rotate(-90)")
        .attr("y", -margin.left + 20)
        .attr("x", -height / 2)
        .text("Month");

    // Create tooltip
    const tooltip = d3.select("body")
        .append("div")
        .style("position", "absolute")
        .style("background-color", "white")
        .style("border", "1px solid #ddd")
        .style("border-radius", "4px")
        .style("padding", "8px")
        .style("pointer-events", "none")
        .style("opacity", 0);

    // Calculate yearly averages and assign colors
    const yearlyData = {};
    const yearsInOrder = [];
    data.forEach(d => {
        const year = d.month.substring(0, 4);
        if (!yearlyData[year]) {
            yearlyData[year] = { count: 0, total: 0, months: [] };
            yearsInOrder.push(year);
        }
        yearlyData[year].count += d.count;
        yearlyData[year].total += 1;
        yearlyData[year].months.push(d.month);
    });

    // Create color mapping (alternating by year)
    const colors = ["steelblue", "skyblue"];
    const yearColorMap = {};
    yearsInOrder.forEach((year, index) => {
        yearColorMap[year] = colors[index % 2];
    });

    const yearlyAverages = Object.keys(yearlyData).map(year => ({
        year: year,
        average: yearlyData[year].count / yearlyData[year].total,
        months: yearlyData[year].months
    }));

    // Draw bars
    svg.selectAll("rect")
        .data(data)
        .enter()
        .append("rect")
        .attr("x", 0)
        .attr("y", d => y(d.month))
        .attr("width", d => x(d.count))
        .attr("height", y.bandwidth())
        .attr("fill", d => {
            const year = d.month.substring(0, 4);
            return yearColorMap[year];
        })
        .style("cursor", "pointer")
        .on("mouseover", function(event, d) {
            d3.select(this).attr("fill", "orange");
            tooltip
                .style("opacity", 1)
                .html(`<strong>${d.month}</strong><br/>Views: ${d.count}`)
                .style("left", (event.pageX + 10) + "px")
                .style("top", (event.pageY - 28) + "px");
        })
        .on("mouseout", function(event, d) {
            const year = d.month.substring(0, 4);
            d3.select(this).attr("fill", yearColorMap[year]);
            tooltip.style("opacity", 0);
        })
        .on("click", function(event, d) {
            // Parse month (YYYY-MM) and navigate to month-views page
            const [year, month] = d.month.split('-');
            window.location.href = `/month-views?year=${year}&month=${month}`;
        });

    // Draw yearly average lines (on top of bars)
    yearlyAverages.forEach(yearData => {
        const firstMonth = yearData.months[0];
        const lastMonth = yearData.months[yearData.months.length - 1];
        const y1 = y(firstMonth) - y.bandwidth() / 2;
        const y2 = y(lastMonth) + y.bandwidth() * 1.5;
        const avgRounded = Math.round(yearData.average);

        // Create a group for line and label
        const lineGroup = svg.append("g")
            .style("cursor", "pointer");

        // Draw the visible dashed line
        const visibleLine = lineGroup.append("line")
            .attr("x1", x(yearData.average))
            .attr("x2", x(yearData.average))
            .attr("y1", y1)
            .attr("y2", y2)
            .attr("stroke", "red")
            .attr("stroke-width", 2)
            .attr("stroke-dasharray", "5,5");

        // Draw invisible wider line for better hover detection
        lineGroup.append("line")
            .attr("x1", x(yearData.average))
            .attr("x2", x(yearData.average))
            .attr("y1", y1)
            .attr("y2", y2)
            .attr("stroke", "transparent")
            .attr("stroke-width", 10);

        // Add text label at top of line
        lineGroup.append("text")
            .attr("x", x(yearData.average))
            .attr("y", y1 - 5)
            .attr("text-anchor", "middle")
            .attr("fill", "red")
            .attr("font-size", "12px")
            .attr("font-weight", "bold")
            .text(`${yearData.year}`);

        // Add hover interactions to the entire group
        lineGroup.on("mouseover", function() {
            visibleLine.attr("stroke-width", 3);

            tooltip
                .style("opacity", 1)
                .html(`<strong>${yearData.year} Average</strong><br/>Views: ${avgRounded}`)
                .style("left", (event.pageX + 10) + "px")
                .style("top", (event.pageY - 28) + "px");
        })
        .on("mousemove", function(event) {
            tooltip
                .style("left", (event.pageX + 10) + "px")
                .style("top", (event.pageY - 28) + "px");
        })
        .on("mouseout", function() {
            visibleLine.attr("stroke-width", 2);
            tooltip.style("opacity", 0);
        });
    });

    // Add legend
    const legend = svg.append("g")
        .attr("transform", `translate(${width - 180}, 10)`);

    // Monthly views - color 1
    legend.append("rect")
        .attr("x", 0)
        .attr("y", 0)
        .attr("width", 20)
        .attr("height", 10)
        .attr("fill", colors[0]);

    legend.append("text")
        .attr("x", 25)
        .attr("y", 10)
        .attr("font-size", "12px")
        .text("Monthly Views (odd years)");

    // Monthly views - color 2
    legend.append("rect")
        .attr("x", 0)
        .attr("y", 18)
        .attr("width", 20)
        .attr("height", 10)
        .attr("fill", colors[1]);

    legend.append("text")
        .attr("x", 25)
        .attr("y", 28)
        .attr("font-size", "12px")
        .text("Monthly Views (even years)");

    // Yearly average line
    legend.append("line")
        .attr("x1", 0)
        .attr("x2", 20)
        .attr("y1", 43)
        .attr("y2", 43)
        .attr("stroke", "red")
        .attr("stroke-width", 2)
        .attr("stroke-dasharray", "5,5");

    legend.append("text")
        .attr("x", 25)
        .attr("y", 48)
        .attr("font-size", "12px")
        .text("Yearly Average");
});
