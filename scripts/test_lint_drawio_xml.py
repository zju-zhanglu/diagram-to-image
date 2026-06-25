"""Regression tests for lint_drawio_xml.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


LINTER = Path(__file__).with_name("lint_drawio_xml.py")


def run_linter(xml: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as temp_dir:
        xml_path = Path(temp_dir) / "diagram.xml"
        xml_path.write_text(textwrap.dedent(xml).strip(), encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(LINTER), str(xml_path)],
            check=False,
            text=True,
            capture_output=True,
        )


class LintDrawioXmlTests(unittest.TestCase):
    def test_visual_child_with_root_parent_fails(self) -> None:
        result = run_linter(
            """
            <mxGraphModel page="1" pageWidth="340" pageHeight="208">
              <root>
                <mxCell id="0"/>
                <mxCell id="1" parent="0"/>
                <mxCell id="root" value="Root" style="rounded=1;arcSize=1;swimlane;startSize=30;fontFamily=PingFang SC;fontSize=16;whiteSpace=wrap;html=1;" vertex="1" parent="1">
                  <mxGeometry x="20" y="20" width="300" height="168" as="geometry"/>
                </mxCell>
                <mxCell id="child" value="Child" style="rounded=1;arcSize=1;whiteSpace=wrap;html=1;fontFamily=PingFang SC;fontSize=14;" vertex="1" parent="1">
                  <mxGeometry x="70" y="88" width="160" height="36" as="geometry"/>
                </mxCell>
              </root>
            </mxGraphModel>
            """
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("visual parent is root but XML parent is 1", result.stdout)

    def test_nested_parent_with_relative_coordinates_passes(self) -> None:
        result = run_linter(
            """
            <mxGraphModel page="1" pageWidth="340" pageHeight="208">
              <root>
                <mxCell id="0"/>
                <mxCell id="1" parent="0"/>
                <mxCell id="root" value="Root" style="rounded=1;arcSize=1;swimlane;startSize=30;fontFamily=PingFang SC;fontSize=16;whiteSpace=wrap;html=1;" vertex="1" parent="1">
                  <mxGeometry x="20" y="20" width="300" height="168" as="geometry"/>
                </mxCell>
                <mxCell id="panel" value="Panel" style="rounded=1;arcSize=1;swimlane;startSize=28;fontFamily=PingFang SC;fontSize=14;whiteSpace=wrap;html=1;" vertex="1" parent="root">
                  <mxGeometry x="20" y="38" width="260" height="120" as="geometry"/>
                </mxCell>
                <mxCell id="leaf-a" value="Leaf A" style="rounded=1;arcSize=1;whiteSpace=wrap;html=1;fontFamily=PingFang SC;fontSize=14;" vertex="1" parent="panel">
                  <mxGeometry x="50" y="36" width="160" height="32" as="geometry"/>
                </mxCell>
                <mxCell id="leaf-b" value="Leaf B" style="rounded=1;arcSize=1;whiteSpace=wrap;html=1;fontFamily=PingFang SC;fontSize=14;" vertex="1" parent="panel">
                  <mxGeometry x="50" y="78" width="160" height="32" as="geometry"/>
                </mxCell>
              </root>
            </mxGraphModel>
            """
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ok=True", result.stdout)

    def test_sibling_leaf_overlap_fails(self) -> None:
        result = run_linter(
            """
            <mxGraphModel page="1" pageWidth="340" pageHeight="208">
              <root>
                <mxCell id="0"/>
                <mxCell id="1" parent="0"/>
                <mxCell id="root" value="Root" style="rounded=1;arcSize=1;swimlane;startSize=30;fontFamily=PingFang SC;fontSize=16;whiteSpace=wrap;html=1;" vertex="1" parent="1">
                  <mxGeometry x="20" y="20" width="300" height="168" as="geometry"/>
                </mxCell>
                <mxCell id="leaf-a" value="Leaf A" style="rounded=1;arcSize=1;whiteSpace=wrap;html=1;fontFamily=PingFang SC;fontSize=14;" vertex="1" parent="root">
                  <mxGeometry x="20" y="38" width="160" height="36" as="geometry"/>
                </mxCell>
                <mxCell id="leaf-b" value="Leaf B" style="rounded=1;arcSize=1;whiteSpace=wrap;html=1;fontFamily=PingFang SC;fontSize=14;" vertex="1" parent="root">
                  <mxGeometry x="100" y="38" width="160" height="36" as="geometry"/>
                </mxCell>
              </root>
            </mxGraphModel>
            """
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sibling overlap between leaf-a and leaf-b", result.stdout)

    def test_direct_child_container_bottom_gap_too_large_fails(self) -> None:
        result = run_linter(
            """
            <mxGraphModel page="1" pageWidth="380" pageHeight="330">
              <root>
                <mxCell id="0"/>
                <mxCell id="1" parent="0"/>
                <mxCell id="root" value="Root" style="rounded=1;arcSize=1;swimlane;startSize=30;fontFamily=PingFang SC;fontSize=16;whiteSpace=wrap;html=1;" vertex="1" parent="1">
                  <mxGeometry x="20" y="20" width="340" height="260" as="geometry"/>
                </mxCell>
                <mxCell id="panel-a" value="Panel A" style="rounded=1;arcSize=1;swimlane;startSize=28;fontFamily=PingFang SC;fontSize=14;whiteSpace=wrap;html=1;" vertex="1" parent="root">
                  <mxGeometry x="20" y="38" width="300" height="80" as="geometry"/>
                </mxCell>
                <mxCell id="panel-b" value="Panel B" style="rounded=1;arcSize=1;swimlane;startSize=28;fontFamily=PingFang SC;fontSize=14;whiteSpace=wrap;html=1;" vertex="1" parent="root">
                  <mxGeometry x="20" y="128" width="300" height="80" as="geometry"/>
                </mxCell>
                <mxCell id="caption" value="说明" style="text;rounded=0;whiteSpace=wrap;html=1;fontFamily=PingFang SC;fontSize=13;" vertex="1" parent="1">
                  <mxGeometry x="20" y="290" width="80" height="20" as="geometry"/>
                </mxCell>
              </root>
            </mxGraphModel>
            """
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("direct content group bottom gap 52px != 10px", result.stdout)

    def test_mixed_direct_children_use_lowest_child_for_bottom_gap(self) -> None:
        result = run_linter(
            """
            <mxGraphModel page="1" pageWidth="380" pageHeight="260">
              <root>
                <mxCell id="0"/>
                <mxCell id="1" parent="0"/>
                <mxCell id="root" value="Root" style="rounded=1;arcSize=1;swimlane;startSize=30;fontFamily=PingFang SC;fontSize=16;whiteSpace=wrap;html=1;" vertex="1" parent="1">
                  <mxGeometry x="20" y="20" width="340" height="220" as="geometry"/>
                </mxCell>
                <mxCell id="panel" value="Panel" style="rounded=1;arcSize=1;swimlane;startSize=28;fontFamily=PingFang SC;fontSize=14;whiteSpace=wrap;html=1;" vertex="1" parent="root">
                  <mxGeometry x="20" y="38" width="300" height="80" as="geometry"/>
                </mxCell>
                <mxCell id="leaf" value="Leaf" style="rounded=1;arcSize=1;whiteSpace=wrap;html=1;fontFamily=PingFang SC;fontSize=14;" vertex="1" parent="root">
                  <mxGeometry x="90" y="178" width="160" height="32" as="geometry"/>
                </mxCell>
              </root>
            </mxGraphModel>
            """
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ok=True", result.stdout)

    def test_leaf_only_group_with_large_vertical_padding_fails(self) -> None:
        result = run_linter(
            """
            <mxGraphModel page="1" pageWidth="340" pageHeight="324">
              <root>
                <mxCell id="0"/>
                <mxCell id="1" parent="0"/>
                <mxCell id="inner-storage" value="" style="rounded=1;arcSize=1;container=1;whiteSpace=wrap;html=1;fontFamily=PingFang SC;fontSize=13;" vertex="1" parent="1">
                  <mxGeometry x="20" y="20" width="300" height="244" as="geometry"/>
                </mxCell>
                <mxCell id="item-storage-1" value="StorageBackend" style="rounded=1;arcSize=1;whiteSpace=wrap;html=1;fontFamily=PingFang SC;fontSize=13;" vertex="1" parent="inner-storage">
                  <mxGeometry x="20" y="83" width="260" height="18" as="geometry"/>
                </mxCell>
                <mxCell id="item-storage-2" value="LocalStorageBackend" style="rounded=1;arcSize=1;whiteSpace=wrap;html=1;fontFamily=PingFang SC;fontSize=13;" vertex="1" parent="inner-storage">
                  <mxGeometry x="20" y="113" width="260" height="18" as="geometry"/>
                </mxCell>
                <mxCell id="item-storage-3" value="S3StorageBackend" style="rounded=1;arcSize=1;whiteSpace=wrap;html=1;fontFamily=PingFang SC;fontSize=13;" vertex="1" parent="inner-storage">
                  <mxGeometry x="20" y="143" width="260" height="18" as="geometry"/>
                </mxCell>
              </root>
            </mxGraphModel>
            """
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("direct content group top padding 83px is too loose", result.stdout)
        self.assertIn("direct content group bottom gap 83px != 10px", result.stdout)

    def test_leaf_only_group_with_compact_padding_passes(self) -> None:
        result = run_linter(
            """
            <mxGraphModel page="1" pageWidth="340" pageHeight="160">
              <root>
                <mxCell id="0"/>
                <mxCell id="1" parent="0"/>
                <mxCell id="inner-storage" value="" style="rounded=1;arcSize=1;container=1;whiteSpace=wrap;html=1;fontFamily=PingFang SC;fontSize=13;" vertex="1" parent="1">
                  <mxGeometry x="20" y="20" width="300" height="108" as="geometry"/>
                </mxCell>
                <mxCell id="item-storage-1" value="StorageBackend" style="rounded=1;arcSize=1;whiteSpace=wrap;html=1;fontFamily=PingFang SC;fontSize=13;" vertex="1" parent="inner-storage">
                  <mxGeometry x="20" y="20" width="260" height="18" as="geometry"/>
                </mxCell>
                <mxCell id="item-storage-2" value="LocalStorageBackend" style="rounded=1;arcSize=1;whiteSpace=wrap;html=1;fontFamily=PingFang SC;fontSize=13;" vertex="1" parent="inner-storage">
                  <mxGeometry x="20" y="50" width="260" height="18" as="geometry"/>
                </mxCell>
                <mxCell id="item-storage-3" value="S3StorageBackend" style="rounded=1;arcSize=1;whiteSpace=wrap;html=1;fontFamily=PingFang SC;fontSize=13;" vertex="1" parent="inner-storage">
                  <mxGeometry x="20" y="80" width="260" height="18" as="geometry"/>
                </mxCell>
              </root>
            </mxGraphModel>
            """
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ok=True", result.stdout)


if __name__ == "__main__":
    unittest.main()
