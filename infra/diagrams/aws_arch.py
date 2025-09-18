#!/usr/bin/env python3
"""Generate AWS architecture diagrams for the PR preview environment."""

import argparse
import os

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import EC2
from diagrams.aws.management import SystemsManager
from diagrams.aws.network import InternetGateway, RouteTable
from diagrams.aws.security import IAMRole
from diagrams.onprem.ci import GithubActions
from diagrams.onprem.client import Client

LABEL_DEFAULTS: dict[str, str] = {
    "GH_OIDC_ROLE_ARN": "IAM Role (OIDC)",
    "PREVIEW_INSTANCE_NAME": "EC2 (PR Preview)",
    "SUBNET_ID": "Public Subnet (subnet-xxxx)",
    "API_SG_ID": "API EC2 (api-sg)",
    "DB_SG_ID": "DB EC2 (db-sg)",
    "VPC_ID": "VPC",
}


def resolve_label(key: str) -> str:
    """Return a label customized by environment variables if provided."""

    return os.getenv(key, LABEL_DEFAULTS[key])


def build_diagram(out_format: str, filename: str) -> None:
    """Render the diagram in the requested format."""

    graph_attr = {"pad": "0.5", "splines": "spline"}
    node_attr = {"fontsize": "12"}
    edge_attr = {"fontsize": "10"}

    preview_label = f"{resolve_label('PREVIEW_INSTANCE_NAME')}\n{resolve_label('API_SG_ID')}"

    with Diagram(
        "Gym Preview AWS Architecture",
        filename=filename,
        outformat=out_format,
        show=False,
        graph_attr=graph_attr,
        node_attr=node_attr,
        edge_attr=edge_attr,
    ):
        developer = Client("Developer Mac")
        ssm = SystemsManager("AWS Systems Manager\n(Port Forwarding)")
        github_actions = GithubActions("GitHub Actions\nPR Workflow")
        iam_role = IAMRole(resolve_label("GH_OIDC_ROLE_ARN"))

        with Cluster(resolve_label("VPC_ID")):
            internet_gateway = InternetGateway("Internet Gateway")
            route_table = RouteTable("Public Route Table")
            with Cluster(resolve_label("SUBNET_ID")):
                api_ec2 = EC2(preview_label)
                db_ec2 = EC2(resolve_label("DB_SG_ID"))

        github_actions >> Edge(label="OIDC AssumeRole", color="darkgreen") >> iam_role
        iam_role >> Edge(label="Provision PR Preview", color="darkgreen") >> api_ec2

        developer >> Edge(label="127.0.0.1:8000", color="royalblue") >> ssm
        ssm >> Edge(label="Port Forwarding", color="royalblue") >> api_ec2
        api_ec2 >> Edge(label="tcp/5432", color="firebrick") >> db_ec2

        route_table >> Edge(style="dotted", color="gray45") >> api_ec2
        route_table >> Edge(style="dotted", color="gray45", label="0.0.0.0/0") >> internet_gateway
        (
            developer
            >> Edge(
                label="Publicアクセス\n(SSM運用では未使用)",
                style="dotted",
                color="gray45",
            )
            >> internet_gateway
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the AWS architecture diagram for the PR preview environment."
    )
    parser.add_argument(
        "--format",
        dest="out_format",
        choices=("png", "svg"),
        default=os.getenv("DIAGRAM_FORMAT", "png"),
        help="Choose the output format (png or svg).",
    )
    parser.add_argument(
        "--filename",
        default=os.getenv("DIAGRAM_FILENAME", "gym-preview-aws"),
        help="Output filename without extension.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_diagram(args.out_format, args.filename)


if __name__ == "__main__":
    main()
