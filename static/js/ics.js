/**
 * ShiftScan - ICS uretimi (RFC 5545)
 * Hem tarayicida (window.ShiftScanICS) hem Node'da (require) calisir.
 */
(function (root, factory) {
    const api = factory();
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = api;
    } else {
        root.ShiftScanICS = api;
    }
})(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    // RFC 5545 icerik satiri siniri: 75 oktet (CRLF haric)
    const MAX_LINE_OCTETS = 75;
    const PRODID = '-//ShiftScan//TR';
    const encoder = new TextEncoder();

    function octets(text) {
        return encoder.encode(text).length;
    }

    /**
     * RFC 5545 TEXT kacisi. Ters bolu once kacirilmali; aksi halde
     * sonradan eklenen kacislar da kacirilir. Satir sonu kacirilmazsa
     * kullanici metni yeni bir ICS ozelligi enjekte edebilir.
     */
    function escapeICSText(value) {
        return String(value == null ? '' : value)
            .replace(/\\/g, '\\\\')
            .replace(/;/g, '\\;')
            .replace(/,/g, '\\,')
            .replace(/\r\n|\r|\n/g, '\\n');
    }

    /** Uzun icerik satirini 75 oktette katlar; devam satirlari bosluk ile baslar. */
    function foldICSLine(line) {
        if (octets(line) <= MAX_LINE_OCTETS) return line;

        const chunks = [];
        let current = '';
        let currentOctets = 0;
        let limit = MAX_LINE_OCTETS;

        for (const char of line) {
            const size = octets(char);
            if (currentOctets + size > limit) {
                chunks.push(current);
                current = char;
                currentOctets = size;
                limit = MAX_LINE_OCTETS - 1; // devam satirlarinda bastaki bosluk sayilir
            } else {
                current += char;
                currentOctets += size;
            }
        }
        chunks.push(current);
        return chunks.join('\r\n ');
    }

    function pad(n) {
        return n < 10 ? '0' + n : '' + n;
    }

    /** Floating local time: YYYYMMDDTHHMMSS */
    function formatLocal(date) {
        return (
            date.getFullYear() +
            pad(date.getMonth() + 1) +
            pad(date.getDate()) +
            'T' +
            pad(date.getHours()) +
            pad(date.getMinutes()) +
            pad(date.getSeconds())
        );
    }

    /** UTC damgasi: YYYYMMDDTHHMMSSZ */
    function formatUTC(date) {
        return date.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');
    }

    function buildICS(events) {
        const stamp = formatUTC(new Date());
        const lines = [
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:' + PRODID,
            'CALSCALE:GREGORIAN'
        ];

        (events || []).forEach(function (ev, index) {
            const dtStart = formatLocal(ev.start);
            lines.push('BEGIN:VEVENT');
            lines.push('UID:shiftscan-' + dtStart + '-' + index + '@shiftscan');
            lines.push('DTSTAMP:' + stamp);
            lines.push('DTSTART:' + dtStart);
            lines.push('DTEND:' + formatLocal(ev.end));
            lines.push('SUMMARY:' + escapeICSText(ev.title));
            if (ev.originalLine) {
                lines.push('DESCRIPTION:' + escapeICSText(ev.originalLine));
            }
            lines.push('END:VEVENT');
        });

        lines.push('END:VCALENDAR');
        return lines.map(foldICSLine).join('\r\n') + '\r\n';
    }

    return { escapeICSText: escapeICSText, foldICSLine: foldICSLine, buildICS: buildICS };
});
