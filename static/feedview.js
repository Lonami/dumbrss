$("span.timestamp").each(function(i, obj)
{
    var time = $(this).attr("data-timestamp");
    $(this).html(moment.unix(time).format("D MMM YYYY"));
    $(this).attr("title", moment.unix(time).format("H:mm"));
});
