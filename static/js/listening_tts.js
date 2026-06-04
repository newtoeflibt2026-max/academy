// Listening TTS - reads from AUDIO_TEXT (JS var) or #transcript / #ttsText elements
(function(){
    var _voices = [];
    var _maleVoice = null;
    var _femaleVoice = null;
    function _loadVoices(){
        _voices = window.speechSynthesis.getVoices();
        var us = _voices.filter(function(v){ return (v.lang||"").toLowerCase().indexOf("en-us") === 0; });
        // Exclude Indian/Asian voices explicitly
        us = us.filter(function(v){ return !/India|Indian|Hindi|Ravi|Heera|Filip|Asia/i.test(v.name); });
        var malePref = ["Guy","Brian","Andrew","Davis","Tony","Eric","Christopher"];
        var femalePref = ["Aria","Jenny","Ava","Emma","Michelle","Sara","Nancy"];
        _maleVoice = us.find(function(v){ return malePref.some(function(n){ return v.name.indexOf(n) >= 0; }); })
                  || us.find(function(v){ return /male/i.test(v.name) && !/female/i.test(v.name); })
                  || us[0] || _voices[0];
        _femaleVoice = us.find(function(v){ return femalePref.some(function(n){ return v.name.indexOf(n) >= 0; }); })
                    || us.find(function(v){ return /female/i.test(v.name); })
                    || us[1] || us[0] || _voices[0];
    }
    if (typeof window !== "undefined" && window.speechSynthesis){
        window.speechSynthesis.onvoiceschanged = _loadVoices;
        _loadVoices();
        setTimeout(_loadVoices, 600);
    }

    function getSourceText(){
        // Priority: AUDIO_TEXT global var > #transcript > #ttsText
        try {
            if (typeof AUDIO_TEXT !== "undefined" && AUDIO_TEXT) return String(AUDIO_TEXT);
        } catch(e) {}
        var el = document.getElementById("transcript") || document.getElementById("ttsText");
        if (el) return el.textContent || el.innerText || "";
        return "";
    }

    function cleanText(t){
        return (t||"").replace(/[\[\]\(\)\*_~`#]/g," ").replace(/\s+/g," ").trim();
    }
    function stripRoles(t){
        // Remove "Word:" patterns (Student:, Professor:, Staff:, Man:, Woman:, etc.)
        return (t||"").replace(/\b[A-Z][a-zA-Z]+\s*:\s*/g, " ");
    }

    window.speakText = function(){
        var raw = getSourceText();
        raw = cleanText(stripRoles(raw));
        if(!raw) return;
        window.speechSynthesis.cancel();
        var u = new SpeechSynthesisUtterance(raw);
        u.lang = "en-US"; u.rate = 0.95; u.pitch = 1.0;
        if(_maleVoice) u.voice = _maleVoice;
        window.speechSynthesis.speak(u);
    };

    window.speakDialog = function(){
        var raw = getSourceText();
        if(!raw) return;
        window.speechSynthesis.cancel();
        var turnRegex = /([A-Z][a-zA-Z]+)\s*:\s*/g;
        var matches = []; var mm;
        while((mm = turnRegex.exec(raw)) !== null){
            matches.push({speaker: mm[1], start: mm.index, contentStart: mm.index + mm[0].length});
        }
        var turns = [];
        for(var i = 0; i < matches.length; i++){
            var cur = matches[i];
            var nextStart = (i+1 < matches.length) ? matches[i+1].start : raw.length;
            var content = raw.substring(cur.contentStart, nextStart).trim();
            if(content) turns.push({speaker: cur.speaker, text: content});
        }
        if(turns.length === 0){
            // No role markers - fall back to single voice
            var u = new SpeechSynthesisUtterance(cleanText(raw));
            u.lang = "en-US"; u.rate = 0.95;
            if(_maleVoice) u.voice = _maleVoice;
            window.speechSynthesis.speak(u);
            return;
        }
        // Assign voices: first speaker = male, second = female
        var speakerVoices = {};
        var assignedCount = 0;
        for(var k = 0; k < turns.length; k++){
            var sp = turns[k].speaker;
            if(!(sp in speakerVoices)){
                speakerVoices[sp] = (assignedCount === 0) ? _maleVoice : _femaleVoice;
                assignedCount++;
            }
        }
        var j = 0;
        function next(){
            if(j >= turns.length) return;
            var t = turns[j++];
            var u = new SpeechSynthesisUtterance(cleanText(t.text));
            u.lang = "en-US"; u.rate = 0.95; u.pitch = 1.0;
            u.voice = speakerVoices[t.speaker] || _maleVoice;
            u.onend = function(){ setTimeout(next, 350); };
            window.speechSynthesis.speak(u);
        }
        next();
    };
})();
