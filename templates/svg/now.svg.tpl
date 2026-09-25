<svg xmlns="http://www.w3.org/2000/svg" width="$w" height="$h" viewBox="0 0 $w $h" role="img" aria-labelledby="title desc">
<title id="title">$title</title>
<desc id="desc">$desc</desc>
<style>
.panel{fill:$surface;stroke:$line}.rule{stroke:$line}.chrome{fill:$faint}.label{fill:$muted}
.txt{fill:$text}.pr{fill:$accent_text}.cover{fill:$surface}.caret{fill:$accent}
.cover{transform-box:fill-box;transform-origin:100% 50%;transform:scaleX(0)}
.mv{opacity:0}
$lines
.blink{animation:blink 1.1s steps(1,end) ${blink_delay}s infinite backwards}
@keyframes type{from{transform:scaleX(1)}to{transform:scaleX(0)}}
@keyframes vis{0%{opacity:1}100%{opacity:0}}
@keyframes hide{from{opacity:0}to{opacity:0}}
@keyframes blink{0%{opacity:0}50%{opacity:1}}
@media (prefers-reduced-motion: reduce){*{animation:none!important}}
</style>
<defs>$defs</defs>
$body
</svg>
