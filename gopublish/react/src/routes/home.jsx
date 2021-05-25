import React from 'react';
import { Badge, Button, Card, CardTitle, CardBody, CardText, Form, FormGroup, Input, Label} from 'reactstrap'
import PropTypes from 'prop-types'


export default function Home() {

    return (
        <div className="container">
        <Card>
          <CardBody>
            <CardTitle tag="h3"><i className="fas fa-home"></i> Welcome to Gopublish !</CardTitle>
            <CardText>
                You can search for a file name or uid using the search bar up top.
            </CardText>
          </CardBody>
        </Card>
        </div>
    );
}
