<svg xmlns="http://www.w3.org/2000/svg" width="$w" height="$h" viewBox="0 0 $w $h" role="img" aria-labelledby="title desc">
<title id="title">$title</title>
<desc id="desc">$desc</desc>
<style>
.panel{fill:$surface;stroke:$line}.sep{stroke:$line}
.val{font:600 ${val_size}px $sans;fill:$text}.lbl{font:400 ${lbl_size}px $sans;fill:$muted}
.ul{stroke:$accent;stroke-width:2;stroke-linecap:round;transform-box:fill-box;transform-origin:0 50%;animation:grow .9s cubic-bezier(.2,.7,.2,1) backwards}
$delays
@keyframes grow{from{transform:scaleX(0)}}
@media (prefers-reduced-motion: reduce){*{animation:none!important}}
</style>
$body
</svg>
