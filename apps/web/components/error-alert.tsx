/**
 * The one red box.
 *
 * The same markup stood in nine components, already drifting; any improvement
 * to it -- a retry hint, an icon, a different border in print -- had to be made
 * nine times or not at all (T-0059).
 */
export function ErrorAlert({ message }: { message: string }) {
  return (
    <div
      role="alert"
      className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-700 dark:text-red-300"
    >
      {message}
    </div>
  );
}
