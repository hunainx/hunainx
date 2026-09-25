<svg xmlns="http://www.w3.org/2000/svg" width="$w" height="$h" viewBox="0 0 $w $h" role="img" aria-labelledby="title desc">
<title id="title">$title</title>
<desc id="desc">$desc</desc>
<style>
.panel{fill:$surface;stroke:$line}.base{stroke:$line}
.bar{fill:$accent;transform-box:fill-box;transform-origin:50% 100%;animation:rise .6s cubic-bezier(.2,.7,.2,1) backwards}
.zero{fill:$line_strong}
.axis{font:400 ${fs}px $mono;fill:$muted}.cap{font:400 ${fs}px $sans;fill:$muted}.capv{font:600 ${fs}px $sans;fill:$text}
$delays
@keyframes rise{from{transform:scaleY(0)}}
@media (prefers-reduced-motion: reduce){*{animation:none!important}}
</style>
$body
</svg>
