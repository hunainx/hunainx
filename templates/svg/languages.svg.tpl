<svg xmlns="http://www.w3.org/2000/svg" width="$w" height="$h" viewBox="0 0 $w $h" role="img" aria-labelledby="title desc">
<title id="title">$title</title>
<desc id="desc">$desc</desc>
<style>
.track{fill:$line}
.seg{transform-box:fill-box;transform-origin:0 50%;animation:grow .8s cubic-bezier(.2,.7,.2,1) backwards}
.lbl{font:400 ${fs}px $sans;fill:$text}.pct{font:400 ${fs}px $mono;fill:$muted}
$delays
@keyframes grow{from{transform:scaleX(0)}}
@media (prefers-reduced-motion: reduce){*{animation:none!important}}
</style>
<defs>$defs</defs>
$body
</svg>
