<svg xmlns="http://www.w3.org/2000/svg" width="$w" height="$h" viewBox="0 0 $w $h" role="img" aria-labelledby="title desc">
<title id="title">$title</title>
<desc id="desc">$desc</desc>
<style>
.name{fill:$text}.sub{fill:$accent_text}.tag,.meta{fill:$muted}
.on{fill:$accent}.off{fill:$line_strong;fill-opacity:.8}.tick{stroke:$faint;fill:none}.rule{stroke:$line}
.rise{animation:rise .9s cubic-bezier(.2,.7,.2,1) backwards}
.r1{animation-delay:.1s}.r2{animation-delay:.25s}.r3{animation-delay:.4s}.r4{animation-delay:.55s}
.dot{transform-box:fill-box;transform-origin:center;animation:dot .5s cubic-bezier(.2,.7,.2,1) backwards}
$delays
.scan{animation:scan 9s cubic-bezier(.45,0,.25,1) 1.6s infinite}
@keyframes rise{from{opacity:0;transform:translateY(6px)}}
@keyframes dot{from{opacity:0;transform:scale(.3)}}
@keyframes scan{0%{transform:translateX(0)}30%,100%{transform:translateX(${scan_dist}px)}}
@media (prefers-reduced-motion: reduce){*{animation:none!important}}
</style>
<defs>$defs</defs>
$body
</svg>
