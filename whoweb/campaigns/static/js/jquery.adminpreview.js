window.addEventListener("load", function () {
    (function ($) {
        var csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        $(".previewslide").click(function () {
            $.ajax({
                type: "POST",
                headers: {'X-CSRFToken': csrftoken},
                url: $(this).attr('id'),
                data:JSON.stringify({
                    "template":$('textarea#id_text').val(),
                    "sender_id":$('input#sender_id').val(),
                    "recipient_id":$('input#recipient_id').val(),
                }),
                context: $(this).parent().parent(),
                success: function (data) {
                    var $html = $(data);
                    $('.previewed').each(function () {
                        $(this).remove();
                    });

                    if (!$html.hasClass('previewed')) {
                        $html.addClass('previewed');
                    }

                    $html.addClass($(this.context).attr('class'));
                    $(".previewslide").after($html);
                }
            });
        });
    })(django.jQuery);
});
