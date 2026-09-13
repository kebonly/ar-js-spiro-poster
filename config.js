/**
 * Poster configuration — the one place to edit.
 *
 * Loaded by both index.html (the AR experience) and print.html (the printable
 * markers). Keeping it in one file means adding a movie updates the app and
 * the print sheet together; they cannot drift apart.
 */
window.SPIRO_AR = (function () {
  'use strict';

  // All distances are in MARKER WIDTHS, where 1.0 is the printed width of a
  // marker's black square. Expressing them this way means the layout stays
  // correct at any print size: print a marker bigger and its video grows with
  // it, in proportion.
  //
  // At an 80mm marker:
  //   width 2.4       -> video renders ~192mm wide
  //   offsetAbove 1.8 -> centred ~144mm above the marker
  var LAYOUT = {
    width:       2.4,    // video width
    offsetAbove: 1.8,    // height of the video's centre above the marker
    bezelPad:    0.16    // border visible around the video
  };

  // Overrides merged over LAYOUT for the barcode markers only.
  //
  // offsetAbove 0 puts the video directly over its marker rather than floating
  // above it. The 1.8 default suits the spiral marker, which has a dedicated
  // clear area above it on the poster — but a barcode marker sits beside a
  // figure with no such space, and 1.8 widths up is off the top of the screen
  // at any normal phone distance. The marker itself stays perfectly readable
  // underneath: detection runs on the raw camera image, not on what we draw
  // over it, so covering the marker on screen does not affect tracking.
  var BARCODE_LAYOUT = {
    offsetAbove: 0
  };

  // ── The movies ────────────────────────────────────────────────────────
  //
  // To add one: drop the .mp4 in assets/video/ and add a line here. The
  // <video> element, the barcode marker, the switcher button, the tap-cycle
  // order and the printable marker sheet are all generated from this list.
  //
  // "barcode" gives the movie its own printed marker, so pointing at that
  // marker plays that movie and nothing else. Valid ids are 0-7: the
  // 3x3_HAMMING63 family has exactly 8, with a minimum pairwise distance of
  // 3 cells, so a single misread cell cannot turn one id into another.
  // Print the matching assets/marker/barcode/barcode-<id>.png.
  //
  // "aspect" is optional — it is read from the file's own dimensions once
  // metadata loads. Set it only to force a different shape.
  //
  // "layout" is optional too: a per-movie override of LAYOUT/BARCODE_LAYOUT,
  // e.g. layout: { width: 1.6 } for a movie that needs a smaller plane.
  var CLIPS = [
    { key: 'cluster', label: 'Cluster', barcode: 1,
      src: 'assets/video/spiro-cluster.mp4' },
    { key: 'flow',    label: 'Flow',    barcode: 0,
      src: 'assets/video/spiro-flow-visualization.mp4' }

    // Six more ids are free (2-7). For example:
    // { key: 'motility', label: 'Motility', barcode: 2,
    //   src: 'assets/video/spiro-motility.mp4' },
  ];

  // The original spiral marker. Unlike the barcode markers it shows several
  // clips, with the switcher buttons and tap-to-cycle. Omitting "clips" means
  // "all of them", so adding a movie above needs no edit here.
  var PATTERN_MARKER = { key: 'spiral', url: 'assets/marker/spiro.patt' };

  return {
    LAYOUT: LAYOUT,
    BARCODE_LAYOUT: BARCODE_LAYOUT,
    CLIPS: CLIPS,
    PATTERN_MARKER: PATTERN_MARKER
  };
})();
