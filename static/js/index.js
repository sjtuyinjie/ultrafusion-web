window.HELP_IMPROVE_VIDEOJS = false;

var INTERP_BASE = "./static/interpolation/stacked";
var NUM_INTERP_FRAMES = 240;

var interp_images = [];
function preloadInterpolationImages() {
  for (var i = 0; i < NUM_INTERP_FRAMES; i++) {
    var path = INTERP_BASE + '/' + String(i).padStart(6, '0') + '.jpg';
    interp_images[i] = new Image();
    interp_images[i].src = path;
  }
}

function setInterpolationImage(i) {
  var image = interp_images[i];
  image.ondragstart = function() { return false; };
  image.oncontextmenu = function() { return false; };
  $('#interpolation-image-wrapper').empty().append(image);
}


$(document).ready(function() {
    function updateNavScrollOffset() {
      var nav = document.querySelector(".uf-nav");
      if (!nav) return;
      var height = Math.ceil(nav.getBoundingClientRect().height);
      document.documentElement.style.setProperty("--uf-nav-height", height + "px");
    }

    function setMobileNavOpen(isOpen) {
      $(".navbar-burger").toggleClass("is-active", isOpen).attr("aria-expanded", isOpen);
      $("#uf-nav-menu").toggleClass("is-active", isOpen);
      $("body").toggleClass("uf-nav-open", isOpen);
      window.requestAnimationFrame(updateNavScrollOffset);
    }

    updateNavScrollOffset();
    $(window).on("resize", updateNavScrollOffset);

    $(".navbar-burger").click(function() {
      setMobileNavOpen(!$(this).hasClass("is-active"));
    });

    $("#uf-nav-menu .navbar-item[href^='#']").on("click", function(event) {
      var targetId = this.getAttribute("href");
      var target = targetId ? document.querySelector(targetId) : null;
      if (!target) return;

      event.preventDefault();
      setMobileNavOpen(false);
      updateNavScrollOffset();
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    });

    $(document).on("click", function(event) {
      if (!$(event.target).closest(".uf-nav").length) {
        setMobileNavOpen(false);
      }
    });

    var options = {
    slidesToScroll: 1,
    slidesToShow: 2.3,
    centerMode: true, // Enable center mode
    loop: true,
    infinite: true,
    autoplay: false,
    autoplaySpeed: 3000,
};

		// Initialize all div with carousel class
    var carousels = bulmaCarousel.attach('.carousel', options);

    // Loop on each carousel initialized
    for(var i = 0; i < carousels.length; i++) {
    	// Add listener to  event
    	carousels[i].on('before:show', state => {
    		console.log(state);
    	});
    }

    // Access to bulmaCarousel instance of an element
    var element = document.querySelector('#my-element');
    if (element && element.bulmaCarousel) {
    	// bulmaCarousel instance is available as element.bulmaCarousel
    	element.bulmaCarousel.on('before-show', function(state) {
    		console.log(state);
    	});
    }

    /*var player = document.getElementById('interpolation-video');
    player.addEventListener('loadedmetadata', function() {
      $('#interpolation-slider').on('input', function(event) {
        console.log(this.value, player.duration);
        player.currentTime = player.duration / 100 * this.value;
      })
    }, false);*/
    var interpolationSlider = $('#interpolation-slider');
    var interpolationWrapper = $('#interpolation-image-wrapper');

    // Interpolation assets were removed in this site version.
    // Only enable that feature when both DOM nodes exist.
    if (interpolationSlider.length && interpolationWrapper.length) {
      preloadInterpolationImages();
      interpolationSlider.on('input', function(event) {
        setInterpolationImage(this.value);
      });
      setInterpolationImage(0);
      interpolationSlider.prop('max', NUM_INTERP_FRAMES - 1);
    }

})
