<svg xmlns="http://www.w3.org/2000/svg" width="$w" height="$h" viewBox="0 0 $w $h" role="img" aria-labelledby="title desc">
<title id="title">$title</title>
<desc id="desc">$desc</desc>
<style>
.panel{fill:$surface;stroke:$line}
.edge{stroke:$accent;stroke-width:2;stroke-linecap:round;stroke-dasharray:${edge_len};animation:draw .8s cubic-bezier(.2,.7,.2,1) .2s backwards}
.name{font:600 ${fs_name}px $mono;fill:$text}.blurb{font:400 ${fs_blurb}px $sans;fill:$muted}.meta{font:400 ${fs_meta}px $sans;fill:$muted}
@keyframes draw{from{stroke-dashoffset:${edge_len}}}
@media (prefers-reduced-motion: reduce){*{animation:none!important}}
</style>
$body
</svg>
