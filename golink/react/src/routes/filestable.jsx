import React, { Component } from 'react'
import axios from 'axios'
import { Badge, Button, Card, CardDeck, CardTitle, CardBody, CardHeader, CardText, Col, Form, FormGroup, Input, Label} from 'reactstrap'
import update from 'react-addons-update'
import { withRouter } from "react-router-dom";
import PropTypes from 'prop-types'
import Utils from '../classes/utils'
import { Link, Redirect } from 'react-router-dom'
import ReactPaginate from 'react-paginate';

export default class FilesTable extends Component {
  constructor (props) {
    super(props)
    this.utils = new Utils()
    this.handlePageClick = this.handlePageClick.bind(this);
  }

  handlePageClick(data) {
    let selected = data.selected;
    let offset = Math.ceil(selected * this.props.config.perPage);
    this.props.getData(offset);
  };

  render () {

    if (this.props.files.length == 0) {
        return (
            <h2 className="text-center">No files available</h2>
        )
    }

    const setStatus = (file_status) => {
        let status = <div></div>
        if (file_status == "available"){
            status = <Badge color="success">Available</Badge>
        }
        if (file_status == "unavailable" || file_status == "failed"){
            status = <Badge color="danger">Unavailable</Badge>
        }
        if (file_status == "pulling"){
            status = <Badge color="secondary">Pulling</Badge>
        }
        if (file_status == "pullable"){
            status = <Badge color="started">Pullable</Badge>
        }
        if (file_status == "starting" || file_status == "hashing"){
            status = <Badge color="warning">Publishing</Badge>
        }
        return status
    }

    let content = this.props.files.map((item, i) => (
        <div key={i}>
        <Card>
          <CardHeader tag="h4">{setStatus(item.status)} <Badge pill color="primary" className="float-right">v{item.version}</Badge></CardHeader>
          <CardBody>
            <CardTitle tag="h3"><i className="fas fa-file"></i> File : <Link to={"/files/" + item.uri}>{item.file_name}</Link></CardTitle>
            <CardText>
            Size : {this.utils.humanFileSize(item.size, true)}
            <br/>
            Published : {item.publishing_date}
            <br/>
            Downloads : {item.downloads}
            </CardText>
          </CardBody>
        </Card>
        </div>
      ))

    return (
      <>
        <h2 className="text-center">{this.props.total} {this.props.total == 1 ? "file" : "files"} found</h2>
        <br/>
        {content}
        <ReactPaginate
          previousLabel={'previous'}
          nextLabel={'next'}
          breakLabel={'...'}
          breakClassName={'break-me'}
          pageCount={this.props.pageCount}
          marginPagesDisplayed={2}
          pageRangeDisplayed={5}
          onPageChange={this.handlePageClick}
          containerClassName={'pagination'}
          subContainerClassName={'pages pagination'}
          activeClassName={'active'}
        />
      </>
    )
  }
}

FilesTable.propTypes = {
  config: PropTypes.object,
  files: PropTypes.array,
  total: PropTypes.number,
  pageCount: PropTypes.number,
  getData: PropTypes.func
}

