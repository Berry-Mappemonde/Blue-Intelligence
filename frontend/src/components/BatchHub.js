import ConsoleShell from "./audit/ConsoleShell";

/**
 * BatchHub — single Console shell (Launch / Rules / Runs / Journal).
 * One launch card per mode, the same tabs everywhere.
 */
export default function BatchHub(props) {
  return <ConsoleShell key={props.mode || "projects"} {...props} />;
}
