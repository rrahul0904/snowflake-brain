import {
  getCandidateSession,
  clearClientBootstrap,
  linkGoogleCandidate,
  loginCandidate,
  logoutCandidate,
  signupCandidate,
} from "./api.js";

let snapshot = { authenticated: false, candidate: null, membership: null };
let hasLoadedCandidate = false;

export function authState() { return snapshot; }
export function candidate() {
  if (!snapshot.candidate) return null;
  const tier = snapshot.membership?.tier || "free";
  const planCode = snapshot.membership?.plan_code || "free";
  const planName = snapshot.membership?.plan?.name || (tier === "premium" ? "Premium" : "Free");
  return {
    ...snapshot.candidate,
    membership: snapshot.membership,
    plan: planName,
    plan_code: planCode,
    entitlement_version: snapshot.membership?.entitlement_version ?? 0,
    sign_in_methods: snapshot.candidate?.sign_in_methods || ["email"],
    is_premium: tier === "premium" && snapshot.membership?.status === "active",
  };
}
export function membership() { return snapshot.membership; }
export function candidateLoaded() { return hasLoadedCandidate; }

function publish(next) {
  snapshot = { ...snapshot, ...next };
  window.dispatchEvent(new CustomEvent("candidate-change", { detail: snapshot }));
  return snapshot;
}

export async function refreshCandidate({ notify = false } = {}) {
  const next = await getCandidateSession();
  hasLoadedCandidate = true;
  if (notify) return publish(next);
  snapshot = { ...snapshot, ...next };
  return snapshot;
}

export async function signUp(payload) {
  clearClientBootstrap("candidate", "readiness");
  const result = await signupCandidate(payload);
  hasLoadedCandidate = true;
  return publish(result);
}

export async function logIn(payload) {
  clearClientBootstrap("candidate", "readiness");
  const result = await loginCandidate(payload);
  hasLoadedCandidate = true;
  return publish(result);
}

export async function linkGoogle(password) {
  clearClientBootstrap("candidate", "readiness");
  const result = await linkGoogleCandidate(password);
  hasLoadedCandidate = true;
  return publish(result);
}

export async function logOut() {
  await logoutCandidate();
  clearClientBootstrap("candidate", "readiness");
  hasLoadedCandidate = true;
  return publish({ authenticated: false, candidate: null, membership: null });
}
