<!doctype html>
<html>
<meta charset="UTF-8">
<title>Bitnomon Testing</title>

<script>
function clearAll() {
    inputs = document.getElementsByTagName("input");
    for (i=0; i<inputs.length; i++) {
        inputs[i].checked = false;
    }
}
</script>

<body>

<h2>Manual Tests</h2>

<ul style="list-style-type:none; padding-left:0">
m4_define(`item', ``<li><input type="checkbox">$1</li>'')

item(`Basic connectivity (covers loading bitcoin.conf)')
item(`All menu items')
item(`Window resizing')
item(`Status bar')
item(`Age axis zooming')
item(`Mempool plot panning fluidity')
item(`Run over 10 mins to check traffic average displays and RRD, and restart')
item(`Saving of window size, position, status bar, network units across restart')
item(`Full screen menu bar hiding, keyboard shortcuts, and WM sync')
item(`pyqtgraph mouse controls: left click panning, right click zooming, scroll
      wheel zooming, all of the above constrained to an axis, lower-left
      auto-zoom button, context menu')
item(`Graceful close on SIGINT (albeit up to 2 second delay)')
item(`Memory usage over 24 hours')
item(`Package build/installation; desktop icon')
item(`No unhandled exceptions')

</ul>

<button onclick="clearAll()">Clear all</button>

</body>
</html>
