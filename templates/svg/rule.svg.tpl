<svg xmlns="http://www.w3.org/2000/svg" width="$w" height="$h" viewBox="0 0 $w $h" role="img" aria-labelledby="title">
<title id="title">$title</title>
<style>
.rule{stroke:$line}.node{fill:$line_strong}
.pulse{animation:pulse 12s cubic-bezier(.45,0,.25,1) 2s 3}
@keyframes pulse{0%{transform:translateX(0)}22%,100%{transform:translateX(${dist}px)}}
@media (prefers-reduced-motion: reduce){*{animation:none!important}}
</style>
<defs><linearGradient id="pg" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="$accent" stop-opacity="0"/><stop offset=".5" stop-color="$accent"/><stop offset="1" stop-color="$accent" stop-opacity="0"/></linearGradient></defs>
$body
</svg>
