/* WHO thick-film counting rule — pure functions, no DOM.
 *
 * Count parasites against white blood cells (WBC), assuming 8,000 WBC/µL:
 *   - fewer than 200 WBC counted        -> keep capturing fields
 *   - >= 200 WBC and >= 100 parasites   -> enough, report
 *   - >= 200 WBC and <  100 parasites   -> keep counting up to 500 WBC
 *   - >= 500 WBC                        -> enough, report
 * See devpost/spec.md > WHO protocol (public/protocol.js).
 */
(function (root) {
  "use strict";

  var WBC_PER_UL = 8000;
  var FIRST_TARGET = 200;
  var EXTENDED_TARGET = 500;
  var PARASITE_THRESHOLD = 100;

  function newSession(reference, sample) {
    return {
      reference: reference,
      startedAt: new Date().toISOString(),
      sample: !!sample,
      fields: [],
      totals: { wbc: 0, parasites: 0 },
    };
  }

  function addField(session, field) {
    var fields = session.fields.concat([field]);
    return Object.assign({}, session, {
      fields: fields,
      totals: {
        wbc: session.totals.wbc + field.wbcCount,
        parasites: session.totals.parasites + field.parasiteCount,
      },
    });
  }

  function guidance(session) {
    var wbc = session.totals.wbc;
    var parasites = session.totals.parasites;
    if (session.fields.length === 0) {
      return { target: FIRST_TARGET, remainingWbc: FIRST_TARGET, canFinish: false, extended: false,
        message: "Upload your first field." };
    }
    if (wbc < FIRST_TARGET) {
      var left = FIRST_TARGET - wbc;
      return { target: FIRST_TARGET, remainingWbc: left, canFinish: false, extended: false,
        message: "Capture another field — " + left + " WBC to go." };
    }
    if (parasites >= PARASITE_THRESHOLD) {
      return { target: FIRST_TARGET, remainingWbc: 0, canFinish: true, extended: false,
        message: "Enough counted — see result." };
    }
    if (wbc < EXTENDED_TARGET) {
      var rest = EXTENDED_TARGET - wbc;
      return { target: EXTENDED_TARGET, remainingWbc: rest, canFinish: false, extended: true,
        message: "Fewer than 100 parasites — keep counting up to 500 WBC (" + rest + " to go)." };
    }
    return { target: EXTENDED_TARGET, remainingWbc: 0, canFinish: true, extended: true,
      message: "Enough counted — see result." };
  }

  function density(session) {
    if (!session.totals.wbc) return null;
    return Math.round((session.totals.parasites * WBC_PER_UL) / session.totals.wbc);
  }

  var api = {
    WBC_PER_UL: WBC_PER_UL,
    newSession: newSession,
    addField: addField,
    guidance: guidance,
    density: density,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Protocol = api;
})(typeof self !== "undefined" ? self : this);
