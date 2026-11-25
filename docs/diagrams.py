#!/usr/bin/env python3
"""Generates docs/architecture-ha.svg and docs/architecture-slim.svg (no dependencies).

Render to PNG with headless Chrome (see docs/render.sh).
"""
from pathlib import Path
from xml.sax.saxutils import escape

W = 1600
FONT = "Helvetica, Arial, sans-serif"

# palette: (fill, stroke)
CLIENT = ("#ffffff", "#5f6b7a")
LB = ("#eef1f5", "#5f6b7a")
BROKER = ("#e3eefe", "#2a62c9")
KRAFT = ("#efe7fd", "#6a3fc4")
COMBINED = ("#e3eefe", "#2a62c9")
SR = ("#e2f5ea", "#1f8a4c")
C3 = ("#fff1e0", "#d4730b")
PROM = ("#fde8e4", "#c4442b")
CFK = ("#f4f4f4", "#333333")
NODE = ("#fafbfc", "#9aa5b1")
NS = ("#ffffff", "#24324a")
TXT = "#1c2733"
EDGE = "#24324a"
METRIC = "#c4442b"


class Svg:
    def __init__(self, h, title):
        self.h = h
        self.parts = []
        self.title = title

    def rect(self, x, y, w, h, colors, rx=10, dash=None, sw=2):
        fill, stroke = colors
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def text(self, x, y, s, size=16, weight="normal", color=TXT, anchor="middle", italic=False):
        st = ' font-style="italic"' if italic else ""
        self.parts.append(
            f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" '
            f'fill="{color}" text-anchor="{anchor}"{st}>{escape(s)}</text>')

    def box(self, x, y, w, h, colors, lines, rx=10, dash=None, sw=2):
        """lines: list of (text, size, weight)."""
        self.rect(x, y, w, h, colors, rx, dash, sw)
        heights = [ln[1] * 1.4 for ln in lines]
        cy = y + (h - sum(heights)) / 2
        for (s, size, weight), lh in zip(lines, heights):
            cy += lh
            self.text(x + w / 2, cy - lh * 0.28, s, size, weight)

    def label(self, x, y, s, size=13, color=EDGE, bg="#ffffff"):
        w = len(s) * size * 0.56 + 10
        self.parts.append(
            f'<rect x="{x - w / 2}" y="{y - size}" width="{w}" height="{size * 1.45}" rx="4" '
            f'fill="{bg}" fill-opacity="0.95"/>')
        self.text(x, y, s, size, "bold", color)

    def arrow(self, pts, color=EDGE, dash=None, both=False, sw=2):
        d = " ".join(f"{'M' if i == 0 else 'L'}{x},{y}" for i, (x, y) in enumerate(pts))
        da = f' stroke-dasharray="{dash}"' if dash else ""
        mk = "m-metric" if color == METRIC else "m-edge"
        start = f' marker-start="url(#{mk}-s)"' if both else ""
        self.parts.append(
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}"{da}{start} '
            f'marker-end="url(#{mk})"/>')

    def save(self, path):
        defs = []
        for mid, col in (("m-edge", EDGE), ("m-metric", METRIC)):
            defs.append(
                f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
                f'markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{col}"/></marker>')
            defs.append(
                f'<marker id="{mid}-s" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="7" '
                f'markerHeight="7" orient="auto"><path d="M10,0 L0,5 L10,10 z" fill="{col}"/></marker>')
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{self.h}" '
            f'viewBox="0 0 {W} {self.h}"><title>{escape(self.title)}</title>'
            f'<defs>{"".join(defs)}</defs>'
            f'<rect width="{W}" height="{self.h}" fill="#ffffff"/>'
            + "".join(self.parts) + "</svg>")
        Path(path).write_text(svg)


def header(s, title, subtitle):
    s.text(W / 2, 42, title, 26, "bold")
    s.text(W / 2, 70, subtitle, 15, color="#5f6b7a")


def clients(s, items):
    """items: list of (x_center, label). Band y=95..155."""
    s.rect(70, 95, 1460, 60, CLIENT, dash="6 4")
    s.text(85, 116, "Clients (outside the cluster)", 13, "bold", "#5f6b7a", anchor="start")
    for x, lab in items:
        s.text(x, 140, lab, 16, "bold")


def right_column(s, ns, prom_cx_out):
    """Schema Registry + Control Center pod on the right. Returns nothing; draws edges to SR/C3."""
    # Schema Registry
    s.box(1090, 370, 210, 110, SR, [("schemaregistry-0", 17, "bold"), ("Schema Registry", 15, "normal"),
                                    ("HTTPS 8081 · basic auth", 13, "normal")])
    # Control Center pod
    s.rect(1090, 560, 440, 250, (C3[0], C3[1]), dash="6 4")
    s.text(1105, 582, f"controlcenter-0 pod", 14, "bold", C3[1], anchor="start")
    s.box(1110, 595, 400, 70, ("#ffffff", C3[1]), [("Control Center 2.7 (next-gen)", 17, "bold"),
                                                   ("HTTPS 9021 · login", 13, "normal")])
    s.box(1110, 715, 190, 75, ("#ffffff", PROM[1]), [("Prometheus", 16, "bold"), ("9090 · OTLP receiver", 13, "normal")])
    s.box(1320, 715, 190, 75, ("#ffffff", PROM[1]), [("Alertmanager", 16, "bold"), ("9093", 13, "normal")])
    s.arrow([(1205, 665), (1205, 713)])
    s.arrow([(1300, 752), (1318, 752)])
    # C3 -> SR
    s.arrow([(1270, 595), (1270, 482)])
    s.label(1270, 525, "HTTPS 8081")


def cfk_and_legend(s, y, crs):
    s.box(70, y, 1460, 62, CFK, [("CFK operator 3.4.1 (Helm, same namespace)", 17, "bold"),
                                 (f"reconciles {crs} · builds keystores/truststores from secret tls-cp", 14, "normal")])


def legend(s, y, extra=None):
    x = 70
    s.arrow([(x, y), (x + 60, y)])
    s.text(x + 72, y + 5, "TLS + authentication (SASL_SSL PLAIN for Kafka, HTTPS + basic auth for SR / C3 / REST)", 14, anchor="start")
    s.arrow([(x + 830, y), (x + 890, y)], METRIC, "7 5")
    s.text(x + 902, y + 5, "metrics push (OTLP)", 14, anchor="start")
    if extra:
        s.text(x + 1090, y + 5, extra, 14, anchor="start", italic=True)


# --------------------------------------------------------------------------------------- HA
def ha(path):
    s = Svg(1110, "Edge CP - HA architecture")
    header(s, "Edge CP - HA (namespace cp-edge-ha, Azure AKS, 3 nodes)",
           "CFK 3.4.1 · Confluent Platform 8.4.1 · Control Center 2.7 · TLS everywhere, SASL_SSL, ACLs, Schema Registry API keys")
    clients(s, [(390, "Python Avro producer / consumer · Kafka clients · REST client"),
                (1195, "Schema Registry clients"), (1425, "Browser")])

    # LoadBalancers
    s.box(70, 210, 960, 62, LB, [("Azure LoadBalancers: kafka.cp-edge-ha.test:9092 (bootstrap) · b0 / b1 / b2.cp-edge-ha.test:9092", 15, "bold"),
                                 ("rest.cp-edge-ha.test:8090 (Kafka REST v3)", 14, "normal")])
    s.box(1090, 210, 210, 62, LB, [("Azure LB", 15, "bold"), ("sr.cp-edge-ha.test:8081", 13, "normal")])
    s.box(1320, 210, 210, 62, LB, [("Azure LB", 15, "bold"), ("c3.cp-edge-ha.test:9021", 13, "normal")])
    s.arrow([(550, 155), (550, 208)]); s.label(550, 188, "SASL_SSL · HTTPS + basic auth")
    s.arrow([(1195, 155), (1195, 208)]); s.label(1195, 188, "HTTPS + API key")
    s.arrow([(1425, 155), (1425, 208)]); s.label(1425, 188, "HTTPS + login")

    # Namespace
    s.rect(40, 295, 1520, 715, NS, rx=14, sw=2.5)
    s.text(55, 318, "AKS · namespace cp-edge-ha", 15, "bold", NS[1], anchor="start")

    xs = [70, 400, 730]
    for i, x in enumerate(xs):
        s.rect(x, 330, 300, 455, NODE, dash="5 4")
        s.text(x + 12, 352, f"node {i + 1} (zone {i + 1})", 14, "bold", "#5f6b7a", anchor="start")
        s.box(x + 20, 370, 260, 150, BROKER, [(f"kafka-{i}", 18, "bold"), ("Broker (Kafka CR)", 15, "normal"),
                                              ("EXTERNAL 9092 · INTERNAL 9071", 13, "normal"),
                                              ("REPLICATION 9072 · REST 8090", 13, "normal")])
        s.box(x + 20, 620, 260, 120, KRAFT, [(f"kraftcontroller-{i}", 18, "bold"), ("KRaft controller", 15, "normal"),
                                             ("CONTROLLER 9074", 13, "normal")])
        s.arrow([(x + 150, 520), (x + 150, 618)])
        s.label(x + 150, 575, "SASL_SSL 9074")
        # LB -> broker
        s.arrow([(x + 150, 272), (x + 150, 368)])
    # replication + quorum
    for a, b in ((xs[0], xs[1]), (xs[1], xs[2])):
        s.arrow([(a + 280, 445), (b + 18, 445)], both=True)
        s.label((a + 280 + b + 20) / 2, 437, "9072", size=12)
        s.arrow([(a + 280, 680), (b + 18, 680)], both=True)
        s.label((a + 280 + b + 20) / 2, 672, "9074", size=12)
    s.text(550, 808, "Raft quorum (3 voters) · RF 3 · min ISR 2 · oneReplicaPerNode", 13, italic=True, color="#5f6b7a")

    right_column(s, None, None)
    s.arrow([(1195, 272), (1195, 368)])
    s.arrow([(1425, 272), (1425, 593)])
    # SR / C3 -> brokers
    s.arrow([(1090, 425), (1012, 425)]); s.label(1050, 417, "9071", size=12)
    s.arrow([(1110, 630), (1060, 630), (1060, 495), (1012, 495)]); s.label(1060, 560, "9071", size=12)

    # metrics bus
    s.parts.append(f'<path d="M220,742 L220,850 L1205,850 L1205,792" fill="none" stroke="{METRIC}" '
                   f'stroke-width="2" stroke-dasharray="7 5" marker-end="url(#m-metric)"/>')
    for x in xs[1:]:
        s.parts.append(f'<path d="M{x + 150},742 L{x + 150},850" fill="none" stroke="{METRIC}" '
                       f'stroke-width="2" stroke-dasharray="7 5"/>')
    s.label(700, 855, "brokers + controllers push metrics (OTLP) to Prometheus :9090", color=METRIC)

    cfk_and_legend(s, 920, "KRaftController, Kafka, SchemaRegistry, ControlCenter, KafkaRestClass, KafkaTopic CRs")
    legend(s, 1050, "KafkaTopic CRs: demo-topic, perf-topic")
    s.save(path)


# ------------------------------------------------------------------------------------- SLIM
def slim(path):
    s = Svg(1110, "Edge CP - slim architecture")
    header(s, "Edge CP - Slim (namespace cp-edge-slim, Colima k3s or Azure AKS, 1 node)",
           "CFK 3.4.1 · Confluent Platform 8.4.1 · Control Center 2.7 · TLS everywhere, SASL_SSL, ACLs, Schema Registry API keys")
    clients(s, [(550, "Python Avro producer / consumer · Kafka clients"),
                (1195, "Schema Registry clients"), (1425, "Browser")])

    s.box(70, 210, 960, 62, LB, [("NodePort (Colima) or Azure LoadBalancer (AKS)", 15, "bold"),
                                 ("kafka.cp-edge-slim.test:31000 → EXTERNAL 9092", 14, "normal")])
    s.box(1090, 210, 210, 62, LB, [("NodePort / LB", 15, "bold"), ("sr.cp-edge-slim.test:31081", 13, "normal")])
    s.box(1320, 210, 210, 62, LB, [("NodePort / LB", 15, "bold"), ("c3.cp-edge-slim.test:31021", 13, "normal")])
    s.arrow([(550, 155), (550, 208)]); s.label(550, 188, "SASL_SSL")
    s.arrow([(1195, 155), (1195, 208)]); s.label(1195, 188, "HTTPS + API key")
    s.arrow([(1425, 155), (1425, 208)]); s.label(1425, 188, "HTTPS + login")

    s.rect(40, 295, 1520, 715, NS, rx=14, sw=2.5)
    s.text(55, 318, "Colima k3s / AKS · namespace cp-edge-slim", 15, "bold", NS[1], anchor="start")

    s.rect(70, 330, 960, 455, NODE, dash="5 4")
    s.text(82, 352, "single node", 14, "bold", "#5f6b7a", anchor="start")
    s.box(230, 380, 640, 300, COMBINED, [
        ("kafka-0", 22, "bold"),
        ("combined broker + KRaft controller", 17, "normal"),
        ("KRaftController CR + configOverrides: process.roles=broker,controller", 14, "normal"),
        ("", 8, "normal"),
        ("EXTERNAL 9092  ·  INTERNAL 9071", 15, "bold"),
        ("REPLICATION 9072  ·  CONTROLLER 9074", 15, "bold"),
        ("all listeners SASL_SSL (PLAIN)", 14, "normal"),
        ("", 8, "normal"),
        ("RF 1 · min ISR 1 · 1 Raft voter", 13, "normal"),
    ])
    s.arrow([(550, 272), (550, 378)])
    # self loop for controller/replication
    s.parts.append(f'<path d="M870,470 C960,470 960,590 872,590" fill="none" stroke="{EDGE}" '
                   f'stroke-width="2" marker-end="url(#m-edge)"/>')
    s.label(955, 535, "9074 / 9072", size=12, bg=NODE[0])
    s.text(955, 555, "to itself", 12, italic=True, color="#5f6b7a")

    right_column(s, None, None)
    s.arrow([(1195, 272), (1195, 368)])
    s.arrow([(1425, 272), (1425, 593)])
    s.arrow([(1090, 425), (872, 425)]); s.label(1050, 417, "9071", size=12)
    s.arrow([(1110, 630), (872, 630)]); s.label(1000, 622, "9071", size=12)

    s.parts.append(f'<path d="M550,680 L550,830 L1205,830 L1205,792" fill="none" stroke="{METRIC}" '
                   f'stroke-width="2" stroke-dasharray="7 5" marker-end="url(#m-metric)"/>')
    s.label(850, 835, "metrics (OTLP) to Prometheus :9090", color=METRIC)

    cfk_and_legend(s, 920, "KRaftController, SchemaRegistry, ControlCenter CRs")
    legend(s, 1050, "Topics: demo-topic, perf-topic (scripts/topics.sh)")
    s.save(path)


if __name__ == "__main__":
    here = Path(__file__).parent
    ha(here / "architecture-ha.svg")
    slim(here / "architecture-slim.svg")
