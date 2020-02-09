$(document).ready(function(){
    // Event called when the notification bell is clicked
    $('.notification').click(function(){
        if(!$(document).find('.notification-dropdown').hasClass('dd')){ // If the notifications list is already being displayed, hide it
            hide_dropdown()
        }else{ // Else display the notifications list
            $('.notification-dropdown').removeClass('dd').addClass('dropdown-transition')
        }
    })


    // Event handler to close the notifications dropdown on clicking outside of it
    $(document).on('click',function(e){
        var target = $(e.target)
        if(!target.closest('.notification').length && !target.closest('.dropdown-transition').length){ // If the user clicks outside of the notifications list
            if(!$(document).find('.notification-dropdown').hasClass('dd')){ // If the notifiations list is found, hide it
                hide_dropdown()
            }
        }
    })

    // Function to close the dropdown
    function hide_dropdown(){
        $(document).find('.notification-dropdown').removeClass('dropdown-transition').addClass('dd')
        $(document).find('.notification-dropdown').find('.list-item').addClass('background-white')
    }
})

// Event called when the "I understand" button for the cookies disclaimer is clicked
$(".close-cookies").click(function(){
    $("#cookies").remove(); // Once clicked, deletes the cookies div
});
