$("span.timestamp").each(function(i, obj)
{
    var time = $(this).attr("data-timestamp");
    $(this).html(moment.unix(time).format("D MMM YYYY"));
    $(this).attr("title", moment.unix(time).format("H:mm"));
});

$("span.star").click(function()
{
    $(this).removeClass("glyphicon-star glyphicon-star-empty");
    if ($(this).attr("data-starred") == "1")
    {
        star = "0";
        $(this).addClass("glyphicon-star-empty");
    }
    else
    {
        star = "1";
        $(this).addClass("glyphicon-star");
    }
    $(this).attr("data-starred", star);
    $.get("/setstarred?id=" + $(this).attr("data-id") + "&f=" + star);
});
