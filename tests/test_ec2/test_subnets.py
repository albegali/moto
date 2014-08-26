# Ensure 'assert_raises' context manager support for Python 2.6
import tests.backport_assert_raises
from nose.tools import assert_raises

import boto
from boto.exception import EC2ResponseError
import sure  # noqa

from moto import mock_ec2


@mock_ec2
def test_subnets():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")

    all_subnets = conn.get_all_subnets()
    all_subnets.should.have.length_of(1)

    conn.delete_subnet(subnet.id)

    all_subnets = conn.get_all_subnets()
    all_subnets.should.have.length_of(0)

    with assert_raises(EC2ResponseError) as cm:
        conn.delete_subnet(subnet.id)
    cm.exception.code.should.equal('InvalidSubnetID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_subnet_create_vpc_validation():
    conn = boto.connect_vpc('the_key', 'the_secret')

    with assert_raises(EC2ResponseError) as cm:
        conn.create_subnet("vpc-abcd1234", "10.0.0.0/18")
    cm.exception.code.should.equal('InvalidVpcID.NotFound')
    cm.exception.status.should.equal(400)
    cm.exception.request_id.should_not.be.none


@mock_ec2
def test_subnet_tagging():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpc = conn.create_vpc("10.0.0.0/16")
    subnet = conn.create_subnet(vpc.id, "10.0.0.0/18")

    subnet.add_tag("a key", "some value")

    tag = conn.get_all_tags()[0]
    tag.name.should.equal("a key")
    tag.value.should.equal("some value")

    # Refresh the subnet
    subnet = conn.get_all_subnets()[0]
    subnet.tags.should.have.length_of(1)
    subnet.tags["a key"].should.equal("some value")


@mock_ec2
def test_get_subnets_filtering():
    conn = boto.connect_vpc('the_key', 'the_secret')
    vpcA = conn.create_vpc("10.0.0.0/16")
    subnetA = conn.create_subnet(vpcA.id, "10.0.0.0/24")
    vpcB = conn.create_vpc("10.0.0.0/16")
    subnetB1 = conn.create_subnet(vpcB.id, "10.0.0.0/24")
    subnetB2 = conn.create_subnet(vpcB.id, "10.0.1.0/24")

    all_subnets = conn.get_all_subnets()
    all_subnets.should.have.length_of(3)

    # Filter by VPC ID
    subnets_by_vpc = conn.get_all_subnets(filters={'vpc-id': vpcB.id})
    subnets_by_vpc.should.have.length_of(2)
    set([subnet.id for subnet in subnets_by_vpc]).should.equal(set([subnetB1.id,subnetB2.id]))

    # Filter by CIDR variations
    subnets_by_cidr1 = conn.get_all_subnets(filters={'cidr': "10.0.0.0/24"})
    subnets_by_cidr1.should.have.length_of(2)
    set([subnet.id for subnet in subnets_by_cidr1]).should.equal(set([subnetA.id,subnetB1.id]))

    subnets_by_cidr2 = conn.get_all_subnets(filters={'cidr-block': "10.0.0.0/24"})
    subnets_by_cidr2.should.have.length_of(2)
    set([subnet.id for subnet in subnets_by_cidr2]).should.equal(set([subnetA.id,subnetB1.id]))

    subnets_by_cidr3 = conn.get_all_subnets(filters={'cidrBlock': "10.0.0.0/24"})
    subnets_by_cidr3.should.have.length_of(2)
    set([subnet.id for subnet in subnets_by_cidr3]).should.equal(set([subnetA.id,subnetB1.id]))

    # Filter by VPC ID and CIDR
    subnets_by_vpc_and_cidr = conn.get_all_subnets(filters={'vpc-id': vpcB.id, 'cidr': "10.0.0.0/24"})
    subnets_by_vpc_and_cidr.should.have.length_of(1)
    set([subnet.id for subnet in subnets_by_vpc_and_cidr]).should.equal(set([subnetB1.id]))

    # Filter by subnet ID
    subnets_by_id = conn.get_all_subnets(filters={'subnet-id': subnetA.id})
    subnets_by_id.should.have.length_of(1)
    set([subnet.id for subnet in subnets_by_id]).should.equal(set([subnetA.id]))

    # Unsupported filter
    conn.get_all_subnets.when.called_with(filters={'not-implemented-filter': 'foobar'}).should.throw(NotImplementedError)
