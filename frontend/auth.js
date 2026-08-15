import {
  getCandidateSession,
  linkGoogleCandidate,
  loginCandidate,
  logoutCandidate,
  signupCandidate,
} from "./api.js";

let snapshot = { authenticated: false, candidate: null, membership: null };

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

function publish(next) {
  snapshot = { ...snapshot, ...next };
  window.dispatchEvent(new CustomEvent("candidate-change", { detail: snapshot }));
  return snapshot;
}

export async function refreshCandidate({ notify = false } = {}) {
  const next = await getCandidateSession();
  if (notify) return publish(next);
  snapshot = { ...snapshot, ...next };
  return snapshot;
}

export async function signUp(payload) {
  const result = await signupCandidate(payload);
  return publish(result);
}

export async function logIn(payload) {
  const result = await loginCandidate(payload);
  return publish(result);
}

export async function linkGoogle(password) {
  const result = await linkGoogleCandidate(password);
  return publish(result);
}

export async function logOut() {
  await logoutCandidate();
  return publish({ authenticated: false, candidate: null, membership: null });
}
