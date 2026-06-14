<?php
/**
 * Ontario Lab Result Importer
 *
 * Auto-imports HL7 ORU^R01 (lab result) messages from the inbox directory
 * into OpenEMR's procedure_report and procedure_result tables.
 *
 * This runs in the mocklab watcher loop - results are automatically
 * imported as soon as they're generated, with no manual steps needed.
 *
 * USAGE: php result_importer.php /path/to/inbox
 */

if ($argc < 2) {
    echo "Usage: php result_importer.php /path/to/inbox\n";
    exit(1);
}

$inbox = $argv[1];
$files = glob("$inbox/RES_*.txt");

if (empty($files)) {
    exit(0);
}

// Direct database connection (no OpenEMR session needed)
$mysqli = new mysqli(
    getenv('MYSQL_HOST') ?: 'openemr-8x-mysql',
    'openemr',
    'openemr',
    'openemr'
);

if ($mysqli->connect_error) {
    error_log("Result importer: DB connection failed: " . $mysqli->connect_error);
    exit(1);
}

/**
 * Parse HL7 v2.3 ORU^R01 (result) message
 * Extracts patient name and lab results
 */
function parse_hl7_result($content) {
    $result = [];

    foreach (explode("\n", trim($content)) as $line) {
        $parts = explode('|', $line);
        $segment = $parts[0];

        if ($segment == 'PID' && count($parts) > 5) {
            // PID|1|pubid|id||name^first^middle||dob|sex
            $name = explode('^', $parts[5]);
            $result['lname'] = $name[0] ?? '';
            $result['fname'] = $name[1] ?? '';
            $result['timestamp'] = date('Y-m-d H:i:s');
        }

        if ($segment == 'OBX' && count($parts) > 7) {
            // OBX|seq|type|code^name^system||value|units|range|status
            if (!isset($result['results'])) {
                $result['results'] = [];
            }

            $code_parts = explode('^', $parts[3]);
            $result['results'][] = [
                'code' => $code_parts[0] ?? '',
                'name' => $code_parts[1] ?? '',
                'value' => $parts[5] ?? '',
                'units' => $parts[6] ?? '',
                'range' => $parts[7] ?? '',
            ];
        }
    }

    return $result;
}

/**
 * Import parsed HL7 result into OpenEMR database
 * Creates procedure_report and procedure_result records
 * Returns true on success, false on failure
 */
function import_result($hl7_result, &$mysqli) {
    if (empty($hl7_result['results'])) {
        return false;
    }

    // Step 1: Find patient by name
    $stmt = $mysqli->prepare(
        "SELECT id FROM patient_data WHERE fname = ? AND lname = ? LIMIT 1"
    );
    $stmt->bind_param("ss", $hl7_result['fname'], $hl7_result['lname']);
    $stmt->execute();
    $pt = $stmt->get_result()->fetch_assoc();
    $stmt->close();

    if (!$pt) {
        error_log("Result importer: Patient not found - {$hl7_result['fname']} {$hl7_result['lname']}");
        return false;
    }

    $patient_id = $pt['id'];

    // Step 2: Find the most recent procedure order for this patient
    $stmt = $mysqli->prepare(
        "SELECT procedure_order_id FROM procedure_order WHERE patient_id = ? ORDER BY procedure_order_id DESC LIMIT 1"
    );
    $stmt->bind_param("i", $patient_id);
    $stmt->execute();
    $ord = $stmt->get_result()->fetch_assoc();
    $stmt->close();

    if (!$ord) {
        error_log("Result importer: No procedure order found for patient id=$patient_id");
        return false;
    }

    $order_id = $ord['procedure_order_id'];

    // Step 3: Create procedure_report (parent record for results)
    $timestamp = $hl7_result['timestamp'];
    $stmt = $mysqli->prepare(
        "INSERT INTO procedure_report (procedure_order_id, date_report, review_status, report_status) VALUES (?, ?, 'received', 'final')"
    );
    $stmt->bind_param("is", $order_id, $timestamp);
    $stmt->execute();
    $report_id = $mysqli->insert_id;
    $stmt->close();

    if (!$report_id) {
        error_log("Result importer: Failed to create procedure_report for order $order_id");
        return false;
    }

    // Step 4: Create procedure_result records (individual lab values)
    foreach ($hl7_result['results'] as $obx) {
        $stmt = $mysqli->prepare(
            "INSERT INTO procedure_result (procedure_report_id, result_code, result_text, date, units, result, `range`, result_status)
             VALUES (?, ?, ?, ?, ?, ?, ?, 'final')"
        );
        $stmt->bind_param(
            "issssss",
            $report_id,
            $obx['code'],
            $obx['name'],
            $timestamp,
            $obx['units'],
            $obx['value'],
            $obx['range']
        );
        $stmt->execute();
        $stmt->close();
    }

    return true;
}

// Process all result files in inbox
foreach ($files as $fpath) {
    $fname = basename($fpath);

    $content = file_get_contents($fpath);
    if (!$content) {
        continue;
    }

    $hl7_result = parse_hl7_result($content);

    if (import_result($hl7_result, $mysqli)) {
        // Success - delete the file so it's not re-imported
        unlink($fpath);
    }
}

$mysqli->close();
?>
