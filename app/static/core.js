$(document).ready(function () {
    // Reload page with 'check' parameter on select change
    $('#checks').on('change', function(){
        var loc = window.location
        var url = loc.href

        var href = new URL(url);

        var searchParams = new URLSearchParams(window.location.search)

        if (searchParams.has('check')){
            href.searchParams.set('check', $(this).val());
            url = href.toString()
        }else{
            // Check if there is other parameter
            if (searchParams.toString()){
                url = loc.origin + loc.pathname + '?check=' + $(this).val() + '&' + searchParams + loc.hash
            }else{
                url = loc.origin + loc.pathname + '?check=' + $(this).val() + loc.hash
            }
        }

        window.location.href = url

    })
})
